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
' SETUP
'   1. Set EXE_PATH below to the real network-share path where
'      slim-report-engine.exe lives. Every lab machine's copy of this
'      module points at the SAME shared path -- ship an update by
'      replacing that one file, never by redistributing this module.
'   2. Import this module into the real Testing Request workbook
'      templates (Chemical/Water/Wafer), assign GenerateReport to a
'      worksheet button (Developer tab > Insert > Button > Assign
'      Macro > GenerateReport).
'
' EXIT-CODE CONTRACT
'   0 -- success; stdout has the generated output file's path
'   1 -- a recognized, actionable data problem (e.g. an unresolved
'        customer/chemical); stderr is safe to show the technician
'        directly
'   2 -- an unexpected error (a real bug); stderr has a traceback --
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

    Dim inputPath As String
    Dim exitCode As Long
    Dim stdOut As String
    Dim stdErr As String

    If Not EnsureSaved(ThisWorkbook) Then
        Exit Sub  ' user cancelled the save prompt
    End If
    inputPath = ThisWorkbook.FullName

    If Not RunReportEngine(inputPath, exitCode, stdOut, stdErr) Then
        MsgBox "Could not start the report engine." & vbCrLf & _
               "Checked path: " & EXE_PATH & vbCrLf & _
               "Is the network share reachable?", vbCritical, "Report Generation Failed"
        Exit Sub
    End If

    Select Case exitCode
        Case 0
            Dim outputPath As String
            outputPath = Trim$(stdOut)
            MsgBox "Report written to:" & vbCrLf & outputPath, vbInformation, "Report Generated"
            OpenOutputFile outputPath
        Case 1
            MsgBox stdErr, vbExclamation, "Report Generation Failed"
        Case Else
            MsgBox "Unexpected error -- contact support with the details below:" & vbCrLf & vbCrLf & stdErr, _
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


' Runs the exe and blocks until it exits or TIMEOUT_SECONDS elapses.
' Returns True if the process actually ran (regardless of ITS OWN exit
' code -- that's read back via the ByRef exitCode/stdOut/stdErr
' parameters). Returns False only when the process could not be
' launched at all (e.g. EXE_PATH isn't reachable).
Private Function RunReportEngine( _
    ByVal inputPath As String, _
    ByRef exitCode As Long, _
    ByRef stdOut As String, _
    ByRef stdErr As String _
) As Boolean

    Dim shellObj As Object
    Dim execObj As Object
    Dim cmd As String
    Dim startTime As Single

    On Error GoTo LaunchFailed

    ' Late-bound (no Tools > References entry needed) -- same pattern
    ' as the WinHttp prototype this was adapted from.
    Set shellObj = CreateObject("WScript.Shell")
    cmd = """" & EXE_PATH & """ """ & inputPath & """"
    Set execObj = shellObj.Exec(cmd)

    ' Timer (seconds since midnight) rather than a Sleep-based counter,
    ' so no Windows API Declare (and its 32-/64-bit Office split) is
    ' needed. Wraps to 0 at midnight -- irrelevant here since
    ' TIMEOUT_SECONDS is a small fraction of a day and this only ever
    ' under-waits by a fraction of a second in the one-in-86400 case a
    ' run starts in the last minute before midnight.
    startTime = Timer
    Do While execObj.Status = 0  ' WshRunning
        DoEvents
        If Timer - startTime > TIMEOUT_SECONDS Then
            execObj.Terminate
            exitCode = -1
            stdErr = "Timed out after " & TIMEOUT_SECONDS & " seconds -- the process was terminated."
            RunReportEngine = True
            Exit Function
        End If
    Loop

    exitCode = execObj.ExitCode
    stdOut = execObj.StdOut.ReadAll()
    stdErr = execObj.StdErr.ReadAll()
    RunReportEngine = True
    Exit Function

LaunchFailed:
    RunReportEngine = False

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
