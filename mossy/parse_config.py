#!/usr/bin/env python3

import ast
import random


class ParseException(Exception):
    pass


class DuplicateRegistration(Exception):
    pass


class NamespaceUnroller(ast.NodeVisitor):
    
    def __init__(self, namespaces):
        self.namespaces = namespaces
    
    def visit_Str(self, node):
        string = node.s
        if ":" not in string:
            return string
        
        prefix, rest = string.split(":", 1)
        extension = self.namespaces.get(prefix, None)
        if extension is not None:
            string = extension + rest
        
        node.original = node.s
        node.s = string


class Config:
    
    def __init__(self, comparer, items, groups, total):
        self.comparer = comparer
        self.items = items
        self.groups = groups
        self.total = total


RESERVED_NAMES = ("named_items", "items", "total")
MACRO_FUNCTIONS = set()

def config_macro(inner):
    MACRO_FUNCTIONS.add(inner.__name__)
    return inner


SAFE_FUNCTIONS = {}
def plugin(name=None):
    """
    This function registers a plugin that can be called from the configuration
    files. The function itself is not a decorator, but returns a decorator. As
    such, it must be called. It does not support positional arguments but only
    keyword arguments. In general, no arguments at all are needed.
    
    The only accepted keyword argument at this time is `name', which defines
    the name with which the plugin is used in the configuration files
    
    Two examples:
    
        @plugin()
        def safe_function_1(*args):
            pass
        
        @plugin(name="safe")
        def name_does_not_matter(*args):
            pass
    
    At this point, the configuration files can refer to the functions
    `safe_function_1` and `safe`.
    """
    
    def decorator(inner):
        nonlocal name # Grab the name of the outer register function
        
        if name is None:
            name = inner.__name__
        if name in SAFE_FUNCTIONS:
            raise DuplicateRegistration(
                "A function named {} has already been registered".format(name))
        if name in ("comparer", "namespaces", "items", "groups"):
            raise DuplicateRegistration(
                "Cannot register a function with name {}".format(name))
        
        SAFE_FUNCTIONS[name] = inner
        
        return inner
    
    return decorator


def evaluate(node, filename, the_globals):
    code = ast.Expression(body=node)
    code.lineno = code.col_offset = 0
    code = compile(code, filename, 'eval')
    return eval(code, the_globals)


def execute_code(root, filename, inner_globals):
    # `root` must be a list containing only assignments and safe calls.
    # The value of each assignment must be a safe expression.
    
    for stmt in root.body:
        if type(stmt) == ast.Expr and type(stmt.value) == ast.Call:
            # This is a call; make sure it is safe to execute
            call_node = stmt.value
            if type(call_node.func) != ast.Name:
                raise ParseException("l.{}: Cannot call an anonymous function."
                                     .format(call_node.func.lineno))
            
            if call_node.func.id in MACRO_FUNCTIONS:
                args = []
                kwargs = {}
                for arg_node in call_node.args:
                    assert_safe_expr(arg_node)
                    args.append(evaluate(arg_node, filename, inner_globals))
                
                for keyword_node in call_node.keywords:
                    assert_safe_expr(keyword_node.value)
                    kwargs[keyword_node.id] = \
                        evaluate(arg_node, filename, inner_globals)
                
                if call_node.starargs is not None:
                    assert_safe_expr(call_node.starargs)
                    stararg = \
                        evaluate(call_node.starargs, filename, inner_globals)
                    args.extend(*stararg)
                
                if call_node.kwargs is not None:
                    assert_safe_expr(call_node.kwargs)
                    kw = evaluate(call_node.kwargs, filename, inner_globals)
                    for key, value in kw.items():
                        if key in kwargs:
                            raise ParseException("l.{}: Got multiple values "
                                                 "for keyword argument '{}'"
                                                 .format(call_node.lineno, key))
                        kwargs[key] = value
                
                if "inner_globals" in kwargs:
                    raise ParseException("l.{}: Illegal keyword name "
                                         "'inner_globals'"
                                         .format(call_node.lineno))
                kwargs["inner_globals"] = inner_globals
                
                globals()[call_node.func.id](*args, **kwargs)
            
            else:
                raise ParseException("l.{}: Illegal call statement."
                                     .format(call_node.lineno))
            
            continue
        
        if type(stmt) != ast.Assign:
            raise ParseException("l.{}: This is not valid code."
                                 .format(stmt.lineno))
        
        if len(stmt.targets) > 1:
            raise ParseException("l.{}: Multiple variable assignment is illegal"
                                 .format(stmt.lineno))
        
        target = stmt.targets[0]
        if target.id in RESERVED_NAMES:
            raise ParseException("l.{}: Assignment to '{}' is illegal"
                                 .format(target.lineno, target.id))
    
        if target.id in SAFE_FUNCTIONS:
            raise ParseException("l.{}: '{}' is already defined as a safe "
                                 "function".format(target.lineno, target.id))
        
        # We must make sure that the expression is safe and will never run
        # user provided code that leads to insecurities in the program
        assert_safe_expr(stmt.value)
        
        # Additionally, if we have namespaces at this point, use it to unroll
        # strings that use that namespace
        if target.id != "namespaces" and "namespaces" in inner_globals:
            NamespaceUnroller(inner_globals["namespaces"]).visit(stmt.value)
        
        if target.id == "groups":
            # The groups assignment must be processed a little differently,
            # since some of the items are identifiers that are part of the
            # 'named_items' dictionary, not the inner_globals. Also, instead of
            # storing the groups exactly as given, we want to store them by
            # the names of the items in the groups. Unnamed items, therefore,
            # must be given an impromptu name. But since the user would then
            # be unable to identify these names, they must be provided back
            # again
            exec_group(stmt.value, filename, inner_globals)
        
        elif target.id in ("comparer", "namespaces"):
            # The 'comparer' and 'namespaces' variables are also special cases
            if target.id == "namespaces":
                # Make sure that this is a valid namespace dictionary
                assert_valid_namespaces(stmt.value)
            
            # We execute the statement as is
            value = evaluate(stmt.value, filename, inner_globals)
            inner_globals[target.id] = value
            
            # Was:
            #   code = ast.Module(body=[stmt])
            #   code.lineno = code.col_offset = 0
            #   code = compile(code, filename, 'exec')
            #   exec(code, inner_globals)
        
        else:
            # This is a regular user-defined item. As such, we execute the
            # assignment by first evaluating the value being assigned, using
            # inner_globals, for global variables, but assign the resulting
            # value to a key in the 'named_items' variable instead.
            value = evaluate(stmt.value, filename, inner_globals)
            inner_globals["named_items"][target.id] = value
    

def exec_group(node, filename, inner_globals):
    # 'groups' must necessarily be a list of sequences. Any sequence type is
    # valid for each individual group (tuples, lists and sets). During
    # evaluation of each group, we use the named_items instead of the
    # inner_globals.
    
    if type(node) != ast.List:
        raise ParseException("l.{}: Expecting a list of groups."
                             .format(node.lineno))
    
    named_items = inner_globals["named_items"]
    
    # As we traverse the groups, we convert them into actual groups
    groups = []
    for group_node in node.elts:
        if type(group_node) not in (ast.Tuple, ast.List, ast.Set):
            raise ParseException("l.{}: Groups must be sequences of items."
                                 .format(group_node.lineno))
        group = []
        for item_node in group_node.elts:
            value = evaluate(item_node, filename, named_items)
            
            if type(item_node) != ast.Name:
                name = str(value)
                named_items[name] = value
            else:
                name = item_node.id
            
            group.append(name)
        
        if type(group_node) == ast.Tuple:
            group = tuple(group)
        elif type(group_node) == ast.Set:
            group = set(group)
        
        groups.append(group)
    
    inner_globals["groups"] = groups


@config_macro
def make_all_pairs(*, inner_globals):
    # Select all named items that are actual items for comparison
    # This are the ones whose name does not start with a underscore '_'.
    names = sorted(i for i in inner_globals["named_items"] if i[0] != '_')
    groups = ((one, two) for one in names for two in names if one <= two)
    inner_globals["groups"] = groups
    inner_globals["total"] = len(names) * (len(names) + 1) // 2


@config_macro
def add_random_pairs(n, *, inner_globals):
    # Select all named items that are actual items for comparison
    # This are the ones whose name does not start with a underscore '_'.
    names = list(i for i in inner_globals["named_items"] if i[0] != '_')
    groups = ((random.choice(names), random.choice(names)) for _ in range(n))
    inner_globals["groups"] = groups
    inner_globals["total"] = inner_globals.get("total", 0) + n


def assert_safe_expr(node):
    # A safe expression is either:
    #   1. a Python literal (string, bytes, number, boolean, or None);
    #   2. an identifier;
    #   3. a Python container that contains only safe expressions
    #      (note that for dictionaries, both keys and values must be safe
    #      expressions);
    #   4. a call to a safe function *by name* with arguments that are safe
    #      expressions; being called by name ensures that we can check whether
    #      the function is safe (a safe callable is defined with the
    #      @plugin decorator).
    
    t = type(node)
    
    if t in (ast.Str, ast.Bytes, ast.Num, ast.NameConstant, ast.Name):
        # node is a valid python literal or an identifier
        pass
    
    elif t in (ast.Tuple, ast.List, ast.Set):
        # Make sure all the elements are safe expressions
        for elt in node.elts:
            assert_safe_expr(elt)
    
    elif t == ast.Dict:
        # Ditto
        for key in node.keys:
            assert_safe_expr(key)
        for value in node.values:
            assert_safe_expr(value)
    
    elif t == ast.Call:
        func_node = node.func
        if type(func_node) != ast.Name:
            raise ParseException("l.{}: Cannot call an anonymous function"
                                 .format(func_node.lineno))
        
        if func_node.id not in SAFE_FUNCTIONS:
            raise ParseException("l.{}: Function {} is not safe"
                                 .format(func_node.lineno, func_node.id))
        
        for arg_node in node.args:
            assert_safe_expr(arg_node)
        for kw_arg in node.keywords:
            assert_safe_expr(kw_arg.value)
        if node.starargs is not None:
            assert_safe_expr(node.starargs)
        if node.kwargs is not None:
            assert_safe_expr(node.kwargs)
    
    else:
        raise ParseException("l.{}: Expressions of type {} are not safe."
                             .format(node.lineno), t)


def assert_valid_namespaces(expr):
    if type(expr) != ast.Dict:
        raise ParseException("l.{}: Expecting a dictionary."
                             .format(expr.lineno))
    
    for key, value in zip(expr.keys, expr.values):
        if type(key) != ast.Str:
            raise ParseException("l.{}: Expecting a string as key."
                             .format(key.lineno))
        if type(value) != ast.Str:
            raise ParseException("l.{}: Expecting a string as value."
                             .format(value.lineno))


REQUIRED = ("comparer", "groups")

def parse_config(files, commands):
    inner_globals = dict(SAFE_FUNCTIONS)
    inner_globals["__builtins__"] = {} # Disable any builtin function
    inner_globals["named_items"] = {} # Store the provided named items
    
    for file in files:
        text = file.read()
        root = ast.parse(text, filename=file.name)
        execute_code(root, file.name, inner_globals)
    
    for text in commands:
        root = ast.parse(text, filename="<execute>")
        execute_code(root, '--execute', inner_globals)
    
    # Make sure we have the necessary variables in the inner_globals dictionary
    for varname in REQUIRED:
        if varname not in inner_globals:
            raise ParseException("Missing the {!r} variable".format(varname))
    
    comparer = inner_globals["comparer"]
    groups = inner_globals["groups"]
    items = inner_globals["named_items"]
    
    if "total" in inner_globals:
        total = inner_globals["total"]
    else:
        total = len(groups)
    
    return Config(comparer, items, groups, total)
