Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\QClawWorkspace\all_in_one"
WshShell.Run "pythonw main.py", 0, False