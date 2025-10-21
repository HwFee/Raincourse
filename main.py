from rich.console import Console

from api.api import RainAPI
from logic import select_menu
from utils.seesion_io import SessionManager
from utils.ui import logo, show_login_method, show_user
from utils.utils import get_files_in_directory

console = Console(width=120, log_time_format="[%Y-%m-%d %H:%M:%S.%f]")


if __name__ == '__main__':
    logo(console)
    try:
        rain = RainAPI(console=console)
        while True:
            show_login_method(console)
            choose = console.input("请选择登录方式: ")
            if choose == "1":
                user_list = get_files_in_directory("user")
                show_user(user_list, console)
                index = console.input("请选择用户: ")
                if int(index) > len(user_list):
                    console.print("[red]输入错误，请重新输入[red]")
                    continue
                rain.user_name = user_list[int(index) - 1]['name']
            elif choose == "2":
                rain.login()
                rain.user_name = rain.get_user_info()['data'][0]['name']
            else:
                console.print("[red]输入错误，请重新输入[red]")
                continue
            SessionManager.manage_session(rain.sees, "user", f"{rain.user_name}.json")
            select_menu(console, rain)
    except Exception as e:
        console.print(f"[red]Error: {e}[red]")
        console.print("[red]Please try again later.[red]")
