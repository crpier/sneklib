from argparse import ArgumentParser
from importlib import import_module

from snek.snektest.runner import test_session

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("import_path", help="Import path to the test")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show additional output during test runs",
    )
    args = parser.parse_args()
    module_part = args.import_path
    rest = ""

    try:
        while module_part != "":
            try:
                module = import_module(module_part)
                break
            except ModuleNotFoundError:
                module_part, rest = module_part.rsplit(".", 1)
        else:
            raise ValueError(f"Failed to import module: {args.import_path}")
    except ValueError:
        print(f"Could not import module: {args.import_path}")
        exit(1)

    if rest == "":
        test_session.run_tests(verbose=args.verbose)
    else:
        target = getattr(module, rest)
        match target:
            # if it's a function:
            case callable:
                test_session.run_tests([target], verbose=args.verbose)
