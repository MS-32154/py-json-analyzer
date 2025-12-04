import ast
import operator
from collections.abc import Callable
from typing import Any

from .logging_config import get_logger

logger = get_logger(__name__)


class FilterExpressionParser:
    """Parse and evaluate safe filter expressions for JSON-like data.

    This class allows evaluating expressions such as:
        - "isinstance(value, int) and value > 10"
        - "key.startswith('user')"
        - "depth <= 3 and 'email' in str(value)"
        - "len(str(value)) > 20"

    Only a limited set of operations and functions are allowed to ensure safety.
    """

    SAFE_OPERATORS: dict[type, Callable[..., Any]] = {
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
    def parse_filter(cls, expression: str) -> Callable[[str, Any, int], bool]:
        """Parse a filter expression and return a callable filter function.

        Args:
            expression: A string containing the filter expression.

        Returns:
            A callable that accepts `key: str`, `value: Any`, and `depth: int`
            and returns a boolean indicating whether the item passes the filter.

        Raises:
            ValueError: If the expression syntax is invalid.

        Examples:
            >>> filter_func = FilterExpressionParser.parse_filter(
            ...     "isinstance(value, int) and value > 10"
            ... )
            >>> filter_func("age", 15, 0)
            True
        """
        logger.info("Parsing filter expression: %s", expression)
        try:
            tree = ast.parse(expression, mode="eval")
            logger.debug("AST successfully parsed for expression: %s", expression)

            def filter_func(key: str, value: Any, depth: int) -> bool:
                env: dict[str, Any] = {
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
                    logger.debug(
                        "Evaluation result for key='%s', value='%s', depth=%d: %s",
                        key,
                        value,
                        depth,
                        cls._eval_node(tree.body, env),
                    )
                    return cls._eval_node(tree.body, env)
                except Exception as e:
                    logger.warning(
                        "Filter evaluation failed for key='%s', value='%s', depth=%d: %s",
                        key,
                        value,
                        depth,
                        e,
                    )
                    return False

            return filter_func

        except SyntaxError as e:
            logger.error("Invalid filter expression syntax: %s", e)
            raise ValueError(f"Invalid filter expression syntax: {e}") from e

    @classmethod
    def _eval_node(cls, node: ast.AST, env: dict[str, Any]) -> Any:
        """Safely evaluate an AST node.

        Args:
            node: The AST node to evaluate.
            env: Dictionary of allowed variables and functions.

        Returns:
            The evaluated value.

        Raises:
            ValueError: If the node type or operator is unsupported.
            NameError: If a variable is undefined.
        """
        if isinstance(node, ast.Constant):
            logger.debug("Evaluating constant: %s", node.value)
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in env:
                logger.debug("Resolving name: %s -> %s", node.id, env[node.id])
                return env[node.id]
            logger.error(f"Name '{node.id}' is not defined")
            raise NameError(f"Name '{node.id}' is not defined")
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left, env)
            right = cls._eval_node(node.right, env)
            op_func = cls.SAFE_OPERATORS.get(type(node.op))
            if op_func:
                logger.debug(
                    "Evaluated BinOp: %s %s %s -> %s",
                    left,
                    node.op,
                    right,
                    op_func(left, right),
                )
                return op_func(left, right)
            logger.error(f"Unsupported operator: {type(node.op)}")
            raise ValueError(f"Unsupported operator: {type(node.op)}")
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand, env)
            op_func = cls.SAFE_OPERATORS.get(type(node.op))
            if op_func:
                logger.debug(
                    "Evaluated UnaryOp: %s %s -> %s", node.op, operand, op_func(operand)
                )
                return op_func(operand)
            logger.error(f"Unsupported unary operator: {type(node.op)}")
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        elif isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, env)
            result = True
            for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
                right = cls._eval_node(comparator, env)
                op_func = cls.SAFE_OPERATORS.get(type(op))
                if op_func:
                    partial = op_func(left, right)
                    logger.debug(
                        "Evaluated Compare: %s %s %s -> %s", left, op, right, partial
                    )
                    result = result and op_func(left, right)
                    left = right
                else:
                    logger.error(f"Unsupported comparison operator: {type(op)}")
                    raise ValueError(f"Unsupported comparison operator: {type(op)}")
            return result
        elif isinstance(node, ast.BoolOp):
            values = [cls._eval_node(value, env) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                logger.debug("Evaluated BoolOp: %s -> %s", node.op, any(values))
                return any(values)
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in env and callable(env[func_name]):
                args = [cls._eval_node(arg, env) for arg in node.args]
                kwargs = {kw.arg: cls._eval_node(kw.value, env) for kw in node.keywords}
                logger.debug(
                    "Called function '%s' with args=%s, kwargs=%s -> %s",
                    func_name,
                    args,
                    kwargs,
                    env[func_name](*args, **kwargs),
                )
                return env[func_name](*args, **kwargs)
            logger.error(f"Function '{func_name}' is not available")
            raise ValueError(f"Function '{func_name}' is not available")
        elif isinstance(node, ast.Attribute):
            obj = cls._eval_node(node.value, env)
            logger.debug(
                "Resolved attribute: %s.%s -> %s",
                obj,
                node.attr,
                getattr(obj, node.attr),
            )
            return getattr(obj, node.attr)
        elif isinstance(node, ast.Subscript):
            obj = cls._eval_node(node.value, env)
            key = cls._eval_node(node.slice, env)
            logger.debug("Resolved subscript: %s[%s] -> %s", obj, key, obj[key])
            return obj[key]
        elif isinstance(node, ast.List):
            logger.debug(
                "Evaluated list: %s", [cls._eval_node(item, env) for item in node.elts]
            )
            return [cls._eval_node(item, env) for item in node.elts]
        elif isinstance(node, ast.Tuple):
            logger.debug(
                "Evaluated tuple: %s",
                tuple(cls._eval_node(item, env) for item in node.elts),
            )
            return tuple(cls._eval_node(item, env) for item in node.elts)
        logger.error(f"Unsupported AST node type: {type(node)}")
        raise ValueError(f"Unsupported AST node type: {type(node)}")
