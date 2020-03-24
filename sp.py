import sys, os
import io
import itertools
import socket
from datetime import datetime
import urllib.parse as url_parser
import _thread
# Doc-Comments, ide errors checken
HELP = """    --: beendet Eingabe. Argumente nach --:
        c: führt Programm dann aus
        s <path>: speichert code unter path
    -s   to start a server to run short Python on
    -h    show this help"""
file_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
HELP_FILE = file_dir + "/src/help.txt"
INDEX_FILE = file_dir + "/src/index.html"
REPLACE_CODES = {"output": "<% OUTPUT %>", "result": "<% RESULT %>", "help": "<% HELP %>", "request": "<% REQUEST %>"}
HELP_FILE_ARG = {"encoding": 'utf-8-sig'}


def is_var(c):
    """
    Checks, if c is a variable.
    :param c: the char to chek
    :return: True, if c is a variable
    """
    return ord('a') <= ord(c) <= ord('k') or c == 'o' or ord('x') <= ord(c) <= ord('z')


def get_var_pos(search_str):  # for preprocessor
    """
    Evaluates the position after the first value (maybe in brackets).
    :param search_str: strin to search in
    :return: the index of the char after the first
    """
    if is_var(search_str[0]) or search_str[0].isdigit() or search_str[0] == '(':
        position = 0
        in_bracket = 0
        for i in search_str:
            if i == '(':
                in_bracket += 1
            elif i == ')':
                if in_bracket == 0:
                    break
                in_bracket -= 1
            elif in_bracket <= 0 and not (i.isdigit() or is_var(i) or i in ['m', 'p', 'q', 'w', 'l', 'v']):
                break
            position += 1
        return position
    elif search_str[0] == 'v':  # constants doesn't need to be in brackets
        return 2
    return 0


def to_py(commands):
    """
    Creates Python code out of the short python code.
    The short python code should be splitted.
    :param commands: a list of the commands (each element is a command)
    :return: the python code
    """
    imp = False
    prim = False
    imp_rand = False
    for i in range(len(commands)):  # 'Preprocessor'
        if len(commands[i]) > 0 and commands[i][0] != '_' and commands[i][:3] != "def" and commands[i][0] != 'r':
            # minus
            if "m" in commands[i]:
                while 'm' in commands[i]:
                    tmp = ""
                    pos = 0
                    for j in range(len(commands[i])):
                        if pos != 0:
                            pos -= 1
                        elif commands[i][j] == 'm':
                            pos = get_var_pos(commands[i][j + 1:])
                            zs = commands[i][j + 1:j + 1 + pos]
                            tmp += "(-" + zs + ")"
                        else:
                            tmp += commands[i][j]
                    commands[i] = tmp
            # Squareroot
            if "q" in commands[i]:
                while 'q' in commands[i]:
                    tmp = ""
                    pos = 0
                    for j in range(len(commands[i])):
                        if pos != 0:
                            pos -= 1
                        elif commands[i][j] == 'q':
                            pos = get_var_pos(commands[i][j + 1:])
                            zs = commands[i][j + 1:j + 1 + pos]
                            tmp += zs + "**0.5"
                        else:
                            tmp += commands[i][j]
                    commands[i] = tmp
            # Root
            if "w" in commands[i]:
                while 'w' in commands[i]:
                    tmp = ""
                    pos = 0
                    for j in range(len(commands[i])):
                        if pos != 0:
                            pos -= 1
                        elif commands[i][j] == 'w':
                            pos = get_var_pos(commands[i][j + 1:])
                            if len(commands[i]) <= j + 1 + pos:
                                tmp += commands[i][j + 1:j + 1 + pos] + "**(1/3)"
                            elif commands[i][j + 1 + pos] == ",":
                                z2 = commands[i][j + 2 + pos:j + 2 + pos + get_var_pos(commands[i][j + 2 + pos:])]
                                tmp += z2 + "**(1/" + commands[i][j + 1:j + 1 + pos] + ")"
                                pos = 1 + len(z2) + len(commands[i][j + 1:j + 1 + pos])
                            else:
                                tmp += commands[i][j + 1:j + 1 + pos] + "**(1/3)"
                        else:
                            tmp += commands[i][j]
                    commands[i] = tmp
            # logarithm
            if "l" in commands[i]:
                while commands[i].count('l') > commands[i].count("log"):
                    tmp = ""
                    pos = 0
                    for j in range(len(commands[i])):
                        if pos != 0:
                            pos -= 1
                        elif commands[i][j] == 'l' and commands[i][j:j + 3] != "log":
                            imp = True
                            pos = get_var_pos(commands[i][j + 1:])
                            if len(commands[i]) <= j + 1 + pos:
                                zs = commands[i][j + 1:j + 1 + pos]
                                tmp += "math.log(" + zs + ")"
                            elif commands[i][j + 1 + pos] == ",":
                                z2 = commands[i][j + 2 + pos:j + 2 + pos + get_var_pos(commands[i][j + 2 + pos:])]
                                tmp += "math.log(" + z2 + "," + commands[i][j + 1:j + 1 + pos] + ")"
                                pos = 1 + len(z2) + len(commands[i][j + 1:j + 1 + pos])
                            else:
                                zs = commands[i][j + 1:j + 1 + pos]
                                tmp += "math.log(" + zs + ")"
                            # break
                        else:
                            tmp += commands[i][j]
                    commands[i] = tmp
            # prime numbers
            if 'p' in commands[i]:
                while commands[i].count('p') > commands[i].count("prim"):
                    tmp = ""
                    pos = 0
                    for j in range(len(commands[i])):
                        if pos != 0:
                            pos -= 1
                        elif commands[i][j] == 'p' and commands[i][j + 1] != 'r':
                            pos = get_var_pos(commands[i][j + 1:])
                            zs = commands[i][j + 1:j + 1 + pos]
                            tmp += "prime_test(" + zs + ")"
                            prim = True
                        else:
                            tmp += commands[i][j]
                    commands[i] = tmp
            # constant variables
            if "v" in commands[i]:
                impvorher = imp
                imp = True
                commands[i] = commands[i].replace("v1", "math.pi")
                commands[i] = commands[i].replace("v2", "math.e")
                klammern = 0
                if "v" in commands[i]:
                    for j in range(len(commands[i])):
                        if commands[i][j] == 'v':
                            if commands[i][j + 1] == '3':
                                imp_rand = True
                                imp = impvorher
                                if len(commands[i]) > j + 2 and commands[i][j + 2] == ',':
                                    tmp = commands[i][:j] + "randint("
                                    klammern = 0
                                    for k in range(j + 3, len(commands[i])):
                                        tmp += commands[i][k]
                                        if commands[i][k] == ',' and klammern <= 0:
                                            pos = get_var_pos(commands[i][k + 1:])
                                            tmp += commands[i][k + 1:k + 1 + pos] + ')' + commands[i][k + 1 + pos:]
                                            break
                                        elif commands[i][k] == '(':
                                            klammern += 1
                                        elif commands[i][k] == ')':
                                            klammern -= 1
                                    commands[i] = tmp
                                else:
                                    commands[i] = commands[i][:j] + "random()"
                            elif commands[i][j + 1] == '!':
                                while "v!" in commands[i][j:]:
                                    if "v!" == commands[i][j:j + 2]:
                                        tmp = commands[i][:j] + "math.factorial("
                                        pos = get_var_pos(commands[i][j + 2:])
                                        commands[i] = tmp + commands[i][j + 2:j + 2 + pos] + ")" + commands[i][
                                                                                                   j + 2 + pos:]
                                        j = j + 2 + pos
                                    else:
                                        j += 1
                            else:
                                klammern += 1
                                if commands[i][j + 1] == 'a':
                                    commands[i] = commands[i][:j] + "math." + commands[i][j + 1:j + 5] + "(" + commands[i][j + 5:]
                                else:
                                    commands[i] = commands[i][:j] + "math." + commands[i][j + 1:j + 4] + "(" + commands[i][j + 4:]
                            break
                    commands[i] += ")" * klammern
    if imp or imp_rand:
        append_top = "#imports:\nimport math\n" * imp + "#imports:\nfrom random import *\n" * imp_rand + "\n"
    else:
        append_top = ""
    if prim:
        append_top += "# prim test function:\ndef prime_test(n):\n\tif (n%2 == 0 and n != 2) or n == 1:\n\t\treturn False\n\telif n==2:\n\t\treturn True\n\telse:\n\t\tfor i in range(3, (int)(n/2), 2):\n\t\t\tif n%i == 0:\n\t\t\t\treturn False\n\t\treturn True\n\n# autogenerated code:\n"
    else:
        append_top += "# autogenerated code:\n"
    py_code = ""
    tabs = 0
    current_var = 'a'
    output = True
    current_iter = 0
    l_if = False
    func_tmp = "s"
    tabs_tmp = 0
    ai_tmp = 0
    func_name = ""
    xyz = {'x': "0", 'y': "0", 'z': "0"}
    for command in commands:
        if len(command) > 0:
            if command[0] == '_':
                py_code += "\t" * tabs + command[1:] + "\n"
            elif command[0].isdigit() or command[0] in ['(', 'p', 'm', '['] or (len(command) > 5 and command[:4] == "rand"):
                py_code += "\t" * tabs + current_var + " = " + command + "\n"
                if current_var != 'h':
                    current_var = chr(ord(current_var) + 1)
            elif command[:3] == "def" and func_tmp == "s":
                func_tmp = py_code
                py_code = ""
                func_name = command[3:]
                tabs_tmp = tabs
                tabs = 1
                ai_tmp = current_iter
            elif command[:3] == "for":
                if command[3] == 't':
                    py_code += "\t" * tabs + "o" * (current_iter // 3) + chr(ord('i') + current_iter % 3) + " = 0\n"
                    command = command.replace("!=", "#")
                    command = command.replace("==", "=")
                    command = command.replace("=", "==")
                    command = command.replace("#", "!=")
                    command = command.replace("n", "not ")
                    command = command.replace("u", " and ")
                    py_code += "\t" * tabs + "while (" + command[4:] + "):\n"
                elif ',' in command:
                    py_code += "\t" * tabs + "for " + "o" * (current_iter // 3) + chr(
                        ord('i') + current_iter % 3) + " in range("
                    stelle = 4
                    for num in itertools.takewhile(lambda x: (x != ','), command[3:]):
                        py_code += str(num)
                        stelle += 1
                    py_code += ", "
                    for num in itertools.takewhile(lambda x: x != ' ', command[stelle:]):
                        py_code += str(num)
                    py_code += "):\n"
                else:
                    py_code += "\t" * tabs + "for " + "o" * (current_iter // 3) + chr(
                        ord('i') + current_iter % 3) + " in range("
                    for num in itertools.takewhile(lambda x: x != ' ', command[3:]):
                        py_code += str(num)
                    py_code += "):\n"
                tabs += 1
                current_iter += 1
            elif command[0] == 's':
                tabs -= 1
                if not l_if and func_tmp == "s":
                    current_iter -= 1
                if func_tmp != "s" and tabs < 1:
                    append_top += "def " + func_name + "():\n"
                    func_name = ""
                    c = 'a'
                    while c <= current_var:
                        append_top += "\tglobal " + c + "\n"
                        c = chr(ord(c) + 1)
                    append_top += py_code + "\n"
                    tabs = tabs_tmp
                    py_code = func_tmp
                    current_iter = ai_tmp
                    func_tmp = "s"
                    tabs_tmp = 0
            elif command == "ift" and l_if:  # entspricht else
                py_code += "\t" * tabs + "else:\n"
                tabs += 1
            elif command[:3] == "ift":
                py_code += "\t" * tabs + "if "
                command = command.replace("!=", "#")
                command = command.replace("==", "=")
                command = command.replace("=", "==")
                command = command.replace("#", "!=")
                command = command.replace("n", "not ")
                command = command.replace("u", " and ")
                py_code += command[3:] + ":\n"
                tabs += 1
                l_if = True
            else:
                if is_var(command[0]) and len(command) == 1:
                    if func_tmp == "s":
                        py_code += "\t" * tabs + "print(" + command + ")\n"
                        output = False
                    else:
                        py_code += "\t" * tabs + "return " + command
                elif command[0] == 'r':
                    py_code += "\t" * tabs + "print("
                    tmp = command[1:].split("+")
                    for c in range(len(tmp)):
                        if len(tmp[c]) == 1:
                            tmp[c] = "str(" + tmp[c] + ")"
                    py_code += "+".join(tmp) + ")\n"
                    output = False
                else:
                    if command[0] == 'x' or command[0] == 'y' or command[0] == 'z':
                        xyz[command[0]] = command[1:]
                    else:
                        if is_var(command[0]) and command[1] not in ['+', '-', '*', '/', '%']:
                            py_code += "\t" * tabs + command[0] + " = " + command[1:] + "\n"
                        else:
                            py_code += "\t" * tabs + command[0] + " = " + command + "\n"
                        if ord(current_var) <= ord(command[0]) < ord("h"):
                            current_var = chr(ord(command[0]) + 1)
            py_code = py_code.replace("z", "(" + xyz['z'] + ")")
            py_code = py_code.replace("y", "(" + xyz['y'] + ")")
            py_code = py_code.replace("x", "(" + xyz['x'] + ")")
    if output:
        py_code += "print(a)\n"
    for i in range(ord(current_var) - ord('a') + 1):
        append_top += chr(ord('a') + i) + " = 0\n"
    return append_top + py_code


def process_request(conn, client, content):
    """
    Processes a http request. Therefor it receives, formats and processes the data
    and sends bag the result.
    :param conn: the connection to the client
    :param client: the adress of the client
    :param content: the content of the index.html file
    """
    # receive and check data
    data = conn.recv(4096)
    if not data:
        print("--Received wrong request at:", datetime.now(), "\n\tIP-adr.:", client[0], "\n\tPort:", str(client[1]))
        return
    else:
        print("--Received correct request at:", datetime.now(), "\n\tIP-adr.:", client[0], "\n\tPort:", str(client[1]))
    header_start = data.decode("utf-8").split("\r\n")[0].replace(";;", "\\")
    header_infos = url_parser.unquote(header_start).split(" ")

    if header_infos[1] == "/favicon.ico":
        print("\t--Icon request (ignored)--")
        conn.send("0".encode())
        conn.close()
        return
    else:
        print("\tInfo: " + header_infos[0], header_infos[-1])

    header_infos[1] = header_infos[1][1:]  # remove / at the beginning of request
    # redirect print calls
    prog_log = io.StringIO()
    try:
        content = content.replace(REPLACE_CODES["request"], "\n".join(header_infos[1:-1]))
        if len(header_infos) == 3 and header_infos[1] == "":
            content = content.replace(REPLACE_CODES["result"], "default")
        else:
            # create code
            py_code = to_py(header_infos[1:-1])
            # execute code
            exec(py_code, {'print': lambda s: prog_log.write(str(s) + "\n")})
            content = content.replace(REPLACE_CODES["result"], "succeeded")
    except Exception as e:
        prog_log.write(str(e) + "\n")  # prints to redirected stdout
        content = content.replace(REPLACE_CODES["result"], "failed")
    result = prog_log.getvalue()
    prog_log.close()
    conn.send(content.replace(REPLACE_CODES["output"], result.replace("\n", "<br>")).encode())
    conn.close()


def run_server(server, content):
    """
    Receive the requests and process it in a new thread.
    :param server: the server to host
    :param content: the content of the index.html file, used to create the website
    """
    while True:
        _thread.start_new_thread(process_request, (*server.accept(), content))


def get_ip_address():
    """
    Gets the local, currently used ip-address,
    by sending a request to a server while getting the socketname.
    :return: the ip-address
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.connect(("8.8.8.8", 80))
    ip_adr = udp_socket.getsockname()[0]
    udp_socket.close()
    return ip_adr


# Check for terminal arguments and start the requested service
if len(sys.argv) > 1 and sys.argv[1][:2] == "--":
    content = ""
    if len(sys.argv[1]) >= 3:
        arg = [sys.argv[1][2:]] + sys.argv[2:3]
        comp = False
        if 'c' in arg:
            comp = True
        path = ""
        if 's' in arg:
            path = sys.argv[arg.index('s') + 2]
        if len(path) > 3:  # modify path
            if path[len(path) - 3:] != ".py":
                path += ".py"
        elif path != "":
            path += ".py"

        # get python:
        py_code = to_py(sys.argv[1 + comp + (path != "") * 2:])  # passed code

        if path != "":
            file = open(path, "w")
            file.write(py_code)
            file.close()
        if comp:
            exec(py_code)
elif len(sys.argv) > 1:
    if sys.argv[1][0] == "-":
        if sys.argv[1][1] == "s":  # -s  ->  Server
            print("Starting Server...")
            # create server
            ip_adr = get_ip_address()
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((ip_adr, 80))
            server.listen(1)

            # Read html and run server
            try:
                with open(INDEX_FILE) as epy_file:
                    content = epy_file.read()
                with open(HELP_FILE, **HELP_FILE_ARG) as help_file:
                    info = help_file.read().replace("\n", "<br>").replace("\t", "&ensp;" * 2).replace(" ", "&ensp;")

                _thread.start_new_thread(run_server, (server, content.replace(REPLACE_CODES["help"], info)))
                print("Server started:\n\thostname:", socket.gethostname(), "\n\tip:", ip_adr, "\n\ttime:", datetime.now())
                input("Press Enter to stop.\n")
            except FileNotFoundError:
                print("Error, index.html not found.")
            except Exception:
                print("An unknown exception occurred.")
        else:  # -h or wrong argument
            file = open(HELP_FILE, **HELP_FILE_ARG)
            content = file.read()
            print(HELP)
            print("Legend:\n" + content)
            file.close()
    else:
        file = open(sys.argv[1], "r")
        content = file.read()
        file.close()
        arr = content.replace("\n", " ").split(" ")
        # write python:
        path = ""
        l = len(sys.argv[1]) - 1
        for i in range(l):
            if sys.argv[1][l - i] == '.':
                path = sys.argv[1][:l - i] + ".py"
                break
        file = open(path, "w")
        file.write(to_py(arr))
        file.close()
else:  # live console
    inp = input()
    commands = ""
    while inp[:2] != "--":
        commands += " " + inp
        inp = input()
    arr = inp[2:].split(" ")
    comp = False
    path = ""
    for arg in arr:
        if path == ".":
            path = arg
        elif arg == "c":
            comp = True
        elif arg == "s" and path == "":
            path = "."

    # saving file
    if path == ".":
        print("Wrong path.")
    else:
        if path != "":
            # to python:
            py_code = to_py(commands.split(" "))
            if len(path) > 3:
                if path[len(path) - 3:] != ".py":
                    path += ".py"
            else:
                path += ".py"
            file = open(path, "w")
            file.write(py_code)
            file.close()
            # running commands
            if comp:
                exec(py_code)
        elif comp:
            py_code = to_py(commands.split(" "))
            exec(py_code)
