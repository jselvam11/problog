import itertools

from problog.engine_builtin import check_mode, _builtin_possible
from problog.engine_unify import UnifyError, unify_value
from problog.engine_stack import NODE_TRUE, NODE_FALSE
from problog.logic import Term, Constant, term2list, list2term, _arithmetic_functions, unquote

from .formula import LogicFormulaHAL
from .logic import SymbolicConstant, ValueDimConstant, ValueExpr, DensityConstant




def _builtin_density(term, args=(), target=None, engine=None, callback=None, transform=None, **kwdargs):
    check_mode( (term,), ['c'], functor='density_builtin')
    actions = []
    try:
        node_ids = target.density_nodes[term]
    except:
        raise ValueError("Cannot query density of discrete random variable ({}).".format(term))
    target.density_queries[term] = set()
    for nid in node_ids:
        if nid in target.density_node_body:
            body_node = target.density_node_body[nid]
        else:
            body_node = target.TRUE
        density_name =  target.get_density_name(term, nid)
        density = DensityConstant(density_name)
        target.add_name(density, body_node, target.LABEL_QUERY)
        target.density_queries[term].add(density)
    actions += callback.notifyComplete()
    return False, actions

def _builtin_free(free_variable, args=(), target=None, engine=None, callback=None, transform=None, **kwdargs):
    check_mode( (free_variable,), ['c'], functor='free')
    actions = []
    target.free_variables.add(free_variable)
    actions += callback.notifyResult((free_variable,), is_last=False)
    actions += callback.notifyComplete()
    return True, actions

def _builtin_free_list(free_variables, args=(), target=None, engine=None, callback=None, transform=None, **kwdargs):
    check_mode( (free_variables,), ['l'], functor='free_list')
    free_variables = term2list(free_variables)
    actions = []
    for v in free_variables:
        target.free_variables.add(v)
    actions += callback.notifyResult((free_variables,), is_last=False)
    actions += callback.notifyComplete()
    return True, actions

def get_value_type(value):
    if isinstance(value, int):
        return "point"
    else:
        return "vector"

def create_value(value, value_functor, value_args, value_name, value_type):
    if value_type=="point":
        dimensions = 1
        return ValueExpr(value_functor, value_args, value_name, dimensions)
    else:
        value_list  = term2list(value)
        dimensions = len(value_list)
        return ValueExpr(value_functor, value_args, value_name, dimensions)

def get_value_terms(value, value_type):
    value_terms = []
    for dv in value.dimension_values:
        value_terms.append(dv)
    if value_type=="point":
        value_terms = value_terms[0]
    else:
        value_terms = [vt for vt in value_terms]
        value_terms = list2term(value_terms)
    return value_terms

def _builtin_as(value, term, args=(), target=None, engine=None, callback=None, transform=None, **kwdargs):
    check_mode( (value,term), ['*g'], functor='as')
    #TODO make this function dependent on term
    value_type = get_value_type(value)
    try:
        node_ids = target.density_nodes[term]
    except:
        raise ValueError("The value of a discrete random variable ({}) is not defined.".format(term))
    actions = []
    for nid in node_ids:
        node = target.get_node(nid)
        value_name =  target.get_density_name(term, nid)
        if value_name in target.density_values:
            value = target.density_values[value_name]
            #?is this doing anything here?
        else:
            probability = node.probability
            value_functor = probability.functor
            value_args = [target.create_ast_representation(a) for a in probability.args]

            value = create_value(value, value_functor, value_args, value_name, value_type)
            target.density_values[value_name] = value

        value_terms = get_value_terms(value, value_type)
        term_pass = (Constant(value_terms), term)
        if nid in target.density_node_body:
            pass_node = target.density_node_body[nid]
        else:
            pass_node = 0
        actions += callback.notifyResult(term_pass, node=pass_node, is_last=False)
    actions += callback.notifyComplete()
    return True, actions

def conditionCallback(functor, arg1, arg2, **kwdargs):
    actions = []
    target = kwdargs["target"]
    callback = kwdargs["callback"]
    arg1 = target.create_ast_representation(arg1)
    arg2 = target.create_ast_representation(arg2)
    args = (arg1,arg2)

    cvariables = set()
    for a in args:
        cvariables = cvariables.union(a.cvariables)
    symbolic_condition = SymbolicConstant(functor, args=args, cvariables=cvariables)

    hashed_symbolic = hash(str(symbolic_condition))
    con_node = target.add_atom(identifier=hashed_symbolic, probability=symbolic_condition, source=None)

    args = kwdargs['engine'].create_context((arg1,arg2), parent=kwdargs['context'])
    actions += callback.notifyResult(args, node=con_node, is_last=True, parent=None)
    return True, actions

def booleanCallback(test, call, arg0, arg1, **kwdargs):
    callback = kwdargs['callback']
    if test:
        args = kwdargs['engine'].create_context((arg0,arg1), parent=kwdargs['context'])
        if kwdargs['target'].flag('keep_builtins'):
            call = functor
            name = Term(call, *args)
            node = kwdargs['target'].add_atom(name, None, None, name=name, source='builtin')
            return True, callback.notifyResult(args, node, True)
        else:
            return True, callback.notifyResult(args, NODE_TRUE, True)
    else:
        return True, callback.notifyComplete()

def _builtin_gt(arg1, arg2, engine=None, **kwdargs):
    """``A > B``
        A and B are ground
    """
    check_mode((arg1, arg2), ['gg'], functor='>', **kwdargs)
    a_value = arg1.compute_value(engine.functions)
    b_value = arg2.compute_value(engine.functions)
    if a_value is None or b_value is None:
        return False
    elif isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
        return booleanCallback(a_value>b_value, '>', a_value, b_value, engine=engine, **kwdargs)
    else:
        return conditionCallback(">", a_value, b_value, engine=engine, **kwdargs)





def conditionCallback(functor, arg1, arg2, **kwdargs):
    actions = []
    target = kwdargs["target"]
    callback = kwdargs["callback"]
    arg1 = target.create_ast_representation(arg1)
    arg2 = target.create_ast_representation(arg2)
    args = (arg1,arg2)

    cvariables = set()
    for a in args:
        cvariables = cvariables.union(a.cvariables)
    symbolic_condition = SymbolicConstant(functor, args=args, cvariables=cvariables)

    hashed_symbolic = hash(str(symbolic_condition))
    con_node = target.add_atom(identifier=hashed_symbolic, probability=symbolic_condition, source=None)

    args = kwdargs['engine'].create_context((arg1,arg2), parent=kwdargs['context'])
    actions += callback.notifyResult(args, node=con_node, is_last=True, parent=None)
    return True, actions


def make_comparison_args(arg1, arg2, engine=None, **kwdargs):
    a_values = evaluate_arithemtics(arg1, engine=engine, **kwdargs)
    b_values = evaluate_arithemtics(arg2, engine=engine, **kwdargs)
    ab_values = list(itertools.product(a_values, b_values))
    return ab_values

def _builtin_lt(arg1, arg2, engine=None, target=None, **kwdargs):
    check_mode((arg1, arg2), ['gg'], functor='<', **kwdargs)
    functor = "<"


    ab_values = make_comparison_args(arg1, arg2, engine=engine, target=target, **kwdargs)

    result = []
    for args in ab_values:
        if isinstance(args[0], (int,float)) and isinstance(args[1], (int,float)):

            if args[0]<args[1]:
                result.append((NODE_TRUE,0))
            else:
                result.append((NODE_FALSE,0))

        elif args[0] is None or args[1] is None:
            result.append((NODE_FALSE,0))
        else:
            arg1 = target.create_ast_representation(args[0][0])
            arg2 = target.create_ast_representation(args[1][0])
            body_node1 = args[0][1]
            body_node2 = args[1][1]
            if body_node1 and body_node2:
                body_node = target.add_and((body_node1,body_node2))
            elif body_node1:
                body_node = body_node1
            else:
                body_node = body_node2

            sym_args = (arg1,arg2)

            cvariables = set()
            for a in sym_args:
                cvariables = cvariables.union(a.cvariables)
            symbolic_condition = SymbolicConstant(functor, args=sym_args, cvariables=cvariables)

            hashed_symbolic = hash(str(symbolic_condition))
            con_node = target.add_atom(identifier=hashed_symbolic, probability=symbolic_condition, source=None)
            if body_node:
                pass_node = target.add_and((body_node, con_node))
            else:
                pass_node = con_node
            result.append((sym_args,pass_node))

    return result

# def _builtin_le(arg1, arg2, engine=None, **kwdargs):
#     """``A =< B``
#         A and B are ground
#     """
#     print(arg1)
#     print(arg2)
#     check_mode((arg1, arg2), ['gg'], functor='=<', **kwdargs)
#     a_value = _evaluate_arithemtics(arg1, engine, **kwdargs)
#     b_value = _evaluate_arithemtics(arg2, engine, **kwdargs)
#
#     a_value = (a_value[0])[0]
#     b_value = (b_value[0])[0]
#
#     print(a_value)
#     print(b_value)
#     if a_value is None or b_value is None:
#         return False
#     elif isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
#         return booleanCallback(a_value<=b_value, '=<', a_value, b_value, engine=engine, **kwdargs)
#     else:
#         return conditionCallback("<=", a_value, b_value, engine=engine, **kwdargs)

def _builtin_le(arg1, arg2, engine=None, **kwdargs):
    """``A =< B``
        A and B are ground
    """
    check_mode((arg1, arg2), ['gg'], functor='=<', **kwdargs)
    a_value = compute_function(arg1, engine.functions)
    b_value = compute_function(arg2, engine.functions)
    if a_value is None or b_value is None:
        return False
    elif isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
        return booleanCallback(a_value<=b_value, '=<', a_value, b_value, engine=engine, **kwdargs)
    else:
        return conditionCallback("<=", a_value, b_value, engine=engine, **kwdargs)


def _builtin_ge(arg1, arg2, engine=None, **kwdargs):
    """``A >= B``
        A and B are ground
    """
    check_mode((arg1, arg2), ['gg'], functor='>=', **kwdargs)
    a_value = arg1.compute_value(engine.functions)
    b_value = arg2.compute_value(engine.functions)
    if a_value is None or b_value is None:
        return False
    elif isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
        return booleanCallback(a_value>=b_value, '>=', a_value, b_value, engine=engine, **kwdargs)
    else:
        return conditionCallback(">=", a_value, b_value, engine=engine, **kwdargs)
#
#
# def _builtin_val_neq(a, b, engine=None, **k):
#     """``A =\= B``
#         A and B are ground
#     """
#     check_mode((a, b), ['gg'], functor='=\=', **k)
#     a_value = a.compute_value(engine.functions)
#     b_value = b.compute_value(engine.functions)
#     if a_value is None or b_value is None:
#         return False
#     else:
#         return a_value != b_value
#
#
# def _builtin_val_eq(a, b, engine=None, **k):
#     """``A =:= B``
#         A and B are ground
#     """
#     check_mode((a, b), ['gg'], functor='=:=', **k)
#     a_value = a.compute_value(engine.functions)
#     b_value = b.compute_value(engine.functions)
#     if a_value is None or b_value is None:
#         return False
#     else:
#         return a_value == b_value
#

def _builtin_observation(value, observation, engine=None, **kwdargs):
    check_mode((value, observation), ['gg'], functor='obs_builtin', **kwdargs)
    assert isinstance(value.functor, ValueDimConstant)

    if isinstance(observation, tuple):
        assert len(value)==len(observation)
    v_value = value
    o_value = observation.compute_value(engine.functions)

    if v_value is None or o_value is None:
        return False
    else:
        return conditionCallback("observation", v_value, o_value, engine=engine, **kwdargs)







def compute_function(term, database=None, target=None, engine=None, **k):
    """
    this function was originally in problog.logic.py
    """
    func = term.functor
    args = term.args

    function = _arithmetic_functions.get((unquote(func), len(args)))
    if function is None:
        function = extra_functions.get((unquote(func), len(args)))
        if function is None:
            raise ArithmeticError("Unknown function '%s'/%s" % (func, len(args)))
    try:
        value_lists = []
        for arg in args:
            value_lists.append(evaluate_arithemtics(arg, database=database, target=target, engine=engine, **k))
        args_list = list(itertools.product(*value_lists))
        coinjoined_args_list = []
        for args in args_list:
            cargs = ()
            body_node = 0
            for a, n in args:
                cargs += (a,)
                if n and not body_node:
                    body_node = n
                elif n:
                    body_node = target.add_and(n, body_node)
            coinjoined_args_list.append((cargs, body_node))

        # if None in :
        #     return [None]
        # else:
        result = []
        for cargs in coinjoined_args_list:
            result.append((function(*cargs[0]), cargs[1]))
        return result
    except ValueError as err:
        raise ArithmeticError(err.message)
    except ZeroDivisionError:
        raise ArithmeticError("Division by zero.")

#FIXME
def create_value2(value_functor, value_args, value_name, value_type):
    if value_type=="point":
        dimensions = 1
        return ValueExpr(value_functor, value_args, value_name, dimensions)


def get_distributions(term, args=(), target=None, engine=None, callback=None, transform=None, **kwdargs):
    value_type="point"
    try:
        node_ids = target.density_nodes[term]
    except:
        raise ValueError("The value of a discrete random variable ({}) is not defined.".format(term))
    result = []
    for nid in node_ids:
        node = target.get_node(nid)
        value_name =  target.get_density_name(term, nid)
        if value_name in target.density_values:
            value = target.density_values[value_name]
            # ?is this doing anything here?
        else:
            probability = node.probability
            value_functor = probability.functor
            value_args = [target.create_ast_representation(a) for a in probability.args]

            value = create_value2(value_functor, value_args, value_name, value_type)
            target.density_values[value_name] = value

        value_terms = get_value_terms(value, value_type)
        if nid in target.density_node_body:
            pass_node = target.density_node_body[nid]
        else:
            pass_node = 0

        result.append((value_terms, pass_node))

    return result


def evaluate_arithemtics(term_expression , engine=None, **k):
    b = term_expression
    b_values = []
    if isinstance(b, Constant):
        b_values.append((b.functor,0))
    elif isinstance(term_expression, SymbolicConstant):
        b_values.append((term_expression,0))
    elif isinstance(b, Term) and (unquote(b.functor), b.arity) in _arithmetic_functions:
        b_values = compute_function(b, engine=engine, **k)

    else:
        result = _builtin_possible(b, engine=engine, **k)
        b_values = []
        for r in result:
            b_values += get_distributions(r[0], engine=engine, **k)
    return b_values

def _builtin_is(a, b, engine=None, **k):
    check_mode((a, b), ['*g'], functor='is', **k)
    try:
        b_values = evaluate_arithemtics(b, engine=engine, **k)
        results =  []
        for b_value in b_values:
            if b_value[0] is None:
                continue
            else:
                if isinstance(b_value[0],(int,float)):
                    constant_val = Constant(b_value[0])
                else:
                    constant_val = b_value[0]
                results.append(((constant_val, b), b_value[1]))
        return results
    except UnifyError:
        return []
