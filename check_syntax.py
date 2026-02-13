
import sys
import py_compile

def check_syntax(file_path):
    try:
        py_compile.compile(file_path, doraise=True)
        print("Syntax OK")
    except py_compile.PyCompileError as e:
        print(f"Syntax Error: {e}")

if __name__ == "__main__":
    check_syntax("src/osbridgelcca/desktop_app/widgets/carbon_emission_data/carbon_machinery_widget.py")
