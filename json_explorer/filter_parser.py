import ast
import operator


class FilterExpressionParser:
    """Parse and evaluate filter expressions for search functionality."""

    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.And: lambda x, y: x and y,
        ast.Or: lambda x, y: x or y,
        ast.Not: operator.not_,
    }

    @classmethod
    def parse_filter(cls, expression):
        """
        Parse a filter expression and return a callable filter function.

        Examples:
        - "isinstance(value, int) and value > 10"
        - "key.startswith('user')"
        - "depth <= 3 and 'email' in str(value)"
        - "len(str(value)) > 20"
        """
        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode="eval")

            def filter_func(key: str, value, depth):
                env = {
                    "key": key,
                    "value": value,
                    "depth": depth,
                    "isinstance": isinstance,
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "type": type,
                    "hasattr": hasattr,
                    "getattr": getattr,
                    "NoneType": type(None),
                }

                try:
                    return cls._eval_node(tree.body, env)
                except Exception:
                    return False

            return filter_func

        except SyntaxError as e:
            raise ValueError(f"Invalid filter expression syntax: {e}")

    @classmethod
    def _eval_node(cls, node, env):
        """Safely evaluate an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise NameError(f"Name '{node.id}' is not defined")
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left, env)
            right = cls._eval_node(node.right, env)
            op_func = cls.SAFE_OPERATORS.get(type(node.op))
            if op_func:
                return op_func(left, right)
            raise ValueError(f"Unsupported operator: {type(node.op)}")
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand, env)
            op_func = cls.SAFE_OPERATORS.get(type(node.op))
            if op_func:
                return op_func(operand)
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        elif isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, env)
            result = True
            for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
                right = cls._eval_node(comparator, env)
                op_func = cls.SAFE_OPERATORS.get(type(op))
                if op_func:
                    result = result and op_func(left, right)
                    left = right
                else:
                    raise ValueError(f"Unsupported comparison operator: {type(op)}")
            return result
        elif isinstance(node, ast.BoolOp):
            values = [cls._eval_node(value, env) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in env and callable(env[func_name]):
                args = [cls._eval_node(arg, env) for arg in node.args]
                kwargs = {kw.arg: cls._eval_node(kw.value, env) for kw in node.keywords}
                return env[func_name](*args, **kwargs)
            raise ValueError(f"Function '{func_name}' is not available")
        elif isinstance(node, ast.Attribute):
            obj = cls._eval_node(node.value, env)
            return getattr(obj, node.attr)
        elif isinstance(node, ast.Subscript):
            obj = cls._eval_node(node.value, env)
            key = cls._eval_node(node.slice, env)
            return obj[key]
        elif isinstance(node, ast.List):
            return [cls._eval_node(item, env) for item in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(cls._eval_node(item, env) for item in node.elts)

        raise ValueError(f"Unsupported AST node type: {type(node)}")
