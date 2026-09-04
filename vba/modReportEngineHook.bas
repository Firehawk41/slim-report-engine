Attribute VB_Name = "modReportEngineHook"
'=======================================================================
' SLIM Report Engine -- VBA invocation hook
'=======================================================================
'
' PURPOSE
'   The lab-technician-facing trigger for report generation stays a
'   familiar Excel button. This module owns NO content/formatting/
'   business logic -- it shells out to the slim-report-engine exe and
'   reacts to its exit code. That exe is a SHORT-LIVED PROCESS, not a
'   server: one process per report, started fresh, runs to completion,
'   exits -- there is no persistent service to keep alive, restart, or
'   monitor for uptime. See the project's own README.md ("Invocation
'   from VBA") for the exit-code contract this module implements, and
'   slim_report_engine/cli.py's own docstring for the canonical
'   definition.
'
' WHY .Run, NOT .Exec
'   WScript.Shell.Exec always shows the child process's console window
'   (there is no way to hide it -- a documented WSH limitation), and it
'   only works at all against a console application. .Run's windowStyle
'   argument hides the window from the moment Windows creates the
'   process, so nothing is ever drawn -- zero flicker, not just a very
'   short one. The tradeoff: .Run gives no StdOut/StdErr pipes and no
'   process handle to poll or terminate, so this module gets the exit
'   code/message from --result-file instead, and (using .Run's
'   non-blocking form, not bWaitOnReturn:=True) polls for that file with
'   the SAME DoEvents/timeout loop shape .Exec used to use -- Excel
'   stays responsive and a hang is still detected within
'   TIMEOUT_SECONDS, it just can't be force-killed anymore (no handle to
'   kill). That's an acceptable tradeoff for a process that in practice
'   takes low single-digit seconds.
'
' SETUP
'   1. Set EXE_PATH below to the real network-share path where
'      slim-report-engine.exe lives. Every lab machine's copy of this
'      module points at the SAME shared path -- ship an update by
'      replacing that one file, never by redistributing this module.
'   2. This module is meant to live in ONE central place (e.g. the
'      Personal Macro Workbook or a shared add-in) rather than being
'      imported into every Testing Request workbook -- GenerateReport
'      acts on ActiveWorkbook, not ThisWorkbook, specifically so it
'      works against whatever TR form the technician currently has
'      open, regardless of where this code itself lives. Assign
'      GenerateReport to a worksheet button in each real TR form
'      template (Developer tab > Insert > Button > Assign Macro >
'      GenerateReport) or a Quick Access Toolbar button -- either way,
'      click it with the TR form as the active window.
'
' EXIT-CODE CONTRACT (read from --result-file, first line)
'   0 -- success; the rest of the file is the generated output file's path
'   1 -- a recognized, actionable data problem (e.g. an unresolved
'        customer/chemical); the message is safe to show the technician
'        directly
'   2 -- an unexpected error (a real bug); the message is a traceback --
'        not meant for a technician to action, shown anyway so it can
'        be copied into a bug report
'=======================================================================

Option Explicit

' TODO (private fork only): set to the real network-share path, e.g.
' "\\SERVER\Share\Path\To\slim-report-engine.exe". Left as an obvious
' placeholder here since a real path is deployment-specific -- same
' policy this project already applies to lab_identity.py.
Private Const EXE_PATH As String = "\\SERVER\SHARE\PATH\TO\slim-report-engine.exe"

' Generation should take low single-digit seconds in practice (it's a
' bounded local Excel write, not a network round trip) -- this is a
' safety ceiling against a genuinely hung process, not a tuned
' expectation.
Private Const TIMEOUT_SECONDS As Long = 60


Public Sub GenerateReport()

    Dim targetWorkbook As Workbook
    Dim inputPath As String
    Dim exitCode As Long
    Dim resultText As String

    Set targetWorkbook = ActiveWorkbook
    If targetWorkbook Is Nothing Then
        MsgBox "No workbook is open.", vbExclamation, "Report Generation Failed"
        Exit Sub
    End If

    If Not EnsureSaved(targetWorkbook) Then
        Exit Sub  ' user cancelled the save prompt
    End If
    inputPath = targetWorkbook.FullName

    If Not RunReportEngine(inputPath, exitCode, resultText) Then
        MsgBox "Could not start the report engine." & vbCrLf & _
               "Checked path: " & EXE_PATH & vbCrLf & _
               "Is the network share reachable?", vbCritical, "Report Generation Failed"
        Exit Sub
    End If

    Select Case exitCode
        Case 0
            Dim outputPath As String
            outputPath = Trim$(resultText)
            MsgBox "Report written to:" & vbCrLf & outputPath, vbInformation, "Report Generated"
            OpenOutputFile outputPath
        Case 1
            MsgBox resultText, vbExclamation, "Report Generation Failed"
        Case -1
            MsgBox resultText, vbExclamation, "Report Generation Failed"
        Case Else
            MsgBox "Unexpected error -- contact support with the details below:" & vbCrLf & vbCrLf & resultText, _
                   vbCritical, "Report Generation Failed"
    End Select

End Sub


' Prompts to save if the workbook has unsaved changes -- the report
' engine reads the workbook from DISK, so an in-memory-only edit would
' otherwise silently generate a report from stale data with no warning.
' Returns False if the user cancels.
Private Function EnsureSaved(ByVal wb As Workbook) As Boolean

    If Not wb.Saved Then
        Dim response As VbMsgBoxResult
        response = MsgBox("This workbook has unsaved changes. Save before generating the report?", _
                           vbYesNoCancel Or vbQuestion, "Save Required")
        Select Case response
            Case vbYes
                wb.Save
            Case vbNo
                ' Proceed anyway -- generating from an intentionally
                ' unsaved state (e.g. while testing) is the
                ' technician's call, not this macro's to block.
            Case vbCancel
                EnsureSaved = False
                Exit Function
        End Select
    End If

    EnsureSaved = True

End Function


' Runs the exe HIDDEN (no console window, ever) and blocks until its
' --result-file appears or TIMEOUT_SECONDS elapses. Returns True if the
' process actually launched (regardless of ITS OWN exit code -- that's
' read back via the ByRef exitCode/resultText parameters, sourced from
' the result file since a hidden launch has no stdout/stderr to read).
' Returns False only when the process could not be launched at all
' (e.g. EXE_PATH isn't reachable).
Private Function RunReportEngine( _
    ByVal inputPath As String, _
    ByRef exitCode As Long, _
    ByRef resultText As String _
) As Boolean

    Dim shellObj As Object
    Dim fso As Object
    Dim cmd As String
    Dim resultFile As String
    Dim startTime As Single
    Dim rawContent As String
    Dim splitPos As Long

    On Error GoTo LaunchFailed

    ' Late-bound (no Tools > References entry needed) -- same pattern
    ' as the WinHttp prototype this was adapted from.
    Set shellObj = CreateObject("WScript.Shell")
    Set fso = CreateObject("Scripting.FileSystemObject")

    resultFile = fso.GetSpecialFolder(2).Path & "\" & fso.GetTempName()  ' 2 = TemporaryFolder
    cmd = """" & EXE_PATH & """ """ & inputPath & """ --result-file """ & resultFile & """"

    ' windowStyle:=0 (SW_HIDE) hides the process's window from the
    ' instant Windows creates it. waitOnReturn:=False returns
    ' immediately -- THIS loop (not Run itself) owns the
    ' timeout/DoEvents responsiveness, so Excel never freezes even
    ' though .Run itself gives back no process handle to poll.
    shellObj.Run cmd, 0, False

    startTime = Timer
    Do While Not fso.FileExists(resultFile)
        DoEvents
        If Timer - startTime > TIMEOUT_SECONDS Then
            exitCode = -1
            resultText = "Timed out after " & TIMEOUT_SECONDS & " seconds. The process may still be " & _
                         "running in the background (slim-report-engine.exe) -- check Task Manager " & _
                         "if this keeps happening."
            RunReportEngine = True
            Exit Function
        End If
    Loop

    ' cli.py writes "<exit code>\n<message>" atomically (temp file +
    ' rename) as its LAST action, so FileExists above never observes a
    ' partially-written file.
    rawContent = ReadTextFile(resultFile)
    splitPos = InStr(rawContent, vbLf)
    If splitPos > 0 Then
        exitCode = CLng(Left$(rawContent, splitPos - 1))
        resultText = Mid$(rawContent, splitPos + 1)
    Else
        exitCode = CLng(rawContent)
        resultText = ""
    End If

    On Error Resume Next
    fso.DeleteFile resultFile, True
    On Error GoTo 0

    RunReportEngine = True
    Exit Function

LaunchFailed:
    RunReportEngine = False

End Function


' Reads a whole text file as a single string. Scripting.FileSystemObject
' has no ReadAll-to-string shortcut of its own outside a TextStream.
Private Function ReadTextFile(ByVal path As String) As String
    Dim fso As Object
    Dim stream As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set stream = fso.OpenTextFile(path, 1)  ' 1 = ForReading
    ReadTextFile = stream.ReadAll()
    stream.Close
End Function


' Best-effort: open the generated report for immediate review. Never
' blocks success on this succeeding -- if it fails (e.g. a file
' association issue), the technician already has the path from the
' MsgBox in GenerateReport.
Private Sub OpenOutputFile(ByVal outputPath As String)
    On Error Resume Next
    Workbooks.Open outputPath
    On Error GoTo 0
End Sub
