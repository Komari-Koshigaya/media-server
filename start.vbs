Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
ws.Run "python -m media_server --port 18080", 0, False
WScript.Echo "Media Server 已启动" & vbCrLf & vbCrLf & _
    "管理后台: http://127.0.0.1:18080/admin" & vbCrLf & vbCrLf & _
    "关闭方法: 在任务管理器中结束 python.exe 进程"
