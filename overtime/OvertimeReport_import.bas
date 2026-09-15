Attribute VB_Name = "OvertimeReport"
Option Explicit

'==================================================================
' 초과근무수당 집계
'------------------------------------------------------------------
' 월별 "초과근무수당 개인별 산출내역서" 엑셀 파일을 여러 개 선택하면
' 각 파일에서 다음을 읽어 월별 / 연도별로 합산한다.
'
'   - 오른쪽 [급여 세부내용] 박스의  총 근무시간
'   - 오른쪽 [급여 세부내용] 박스의  시간외(시간)
'
' 왼쪽 일자별 표(1~31일, 합계 열)는 읽지 않는다.
' [급여 세부내용] 텍스트를 앵커로 찾으므로 그 달의 일수(28/29/30/31)나
' 인원 수가 달라도 영향을 받지 않는다.
'==================================================================

' ---- 탐색 키워드 (공백 제거 후 비교) ----
Private Const K_TITLE  As String = "초과근무수당개인별산출내역서"
Private Const K_PERIOD As String = "일집계현황"
Private Const K_BOX    As String = "급여세부내용"
Private Const K_WORK   As String = "총근무시간"
Private Const K_OT     As String = "시간외"

' ---- 결과 시트 ----
Private Const SH_RESULT As String = "집계결과"
Private Const SH_LOG    As String = "처리내역"

' ---- 탐색 범위 상한 ----
Private Const HDR_ROWS  As Long = 30
Private Const HDR_COLS  As Long = 120
Private Const MAX_ROWS  As Long = 5000
Private Const MAX_COLS  As Long = 250
Private Const BOX_DEPTH As Long = 10

' ---- 결과 표 첫 행 ----
Private Const HDR_ROW As Long = 6


'==================================================================
' 진입점 (버튼에 연결됨)
'==================================================================
Public Sub RunAggregate()
    Dim vFiles As Variant
    Dim i As Long, nFile As Long
    Dim dctMonth As Object, dctSeen As Object
    Dim colLog As Collection
    Dim prevCalc As Long
    Dim errN As Long, errD As String

    vFiles = Application.GetOpenFilename( _
        FileFilter:="엑셀 파일 (*.xls;*.xlsx;*.xlsm),*.xls;*.xlsx;*.xlsm", _
        Title:="초과근무수당 산정서 파일 선택  (Ctrl / Shift 로 여러 개 선택)", _
        MultiSelect:=True)

    If Not IsArray(vFiles) Then Exit Sub

    Set dctMonth = CreateObject("Scripting.Dictionary")
    Set dctSeen = CreateObject("Scripting.Dictionary")
    Set colLog = New Collection

    prevCalc = Application.Calculation
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual

    On Error GoTo CleanUp

    nFile = UBound(vFiles) - LBound(vFiles) + 1
    For i = LBound(vFiles) To UBound(vFiles)
        Application.StatusBar = "초과근무수당 집계 - 읽는 중 (" & _
                                (i - LBound(vFiles) + 1) & " / " & nFile & ") ..."
        ProcessFile CStr(vFiles(i)), dctMonth, dctSeen, colLog
    Next i

    WriteResult dctMonth, colLog, nFile

CleanUp:
    errN = Err.Number
    errD = Err.Description
    On Error Resume Next
    Application.StatusBar = False
    Application.Calculation = prevCalc
    Application.EnableEvents = True
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    On Error GoTo 0

    If errN <> 0 Then
        MsgBox "집계 중 오류가 발생했습니다." & vbCrLf & vbCrLf & errD, _
               vbExclamation, "초과근무수당 집계"
    End If
End Sub


'==================================================================
' 파일 1개 처리
'==================================================================
Private Sub ProcessFile(ByVal sPath As String, dctMonth As Object, _
                        dctSeen As Object, colLog As Collection)
    Dim wb As Workbook
    Dim ws As Worksheet, wsT As Worksheet
    Dim colCand As Collection
    Dim sName As String, sKey As String, ship As String, sYmSrc As String
    Dim yr As Long, mo As Long, nPer As Long
    Dim dWork As Double, dOT As Double

    sName = Mid$(sPath, InStrRev(sPath, Application.PathSeparator) + 1)

    ' 집계 파일 자신은 건너뛴다
    If StrComp(sPath, ThisWorkbook.FullName, vbTextCompare) = 0 Then
        colLog.Add Array(sName, "", "", "", "", "", "", "", "", "집계 파일 자신 - 건너뜀")
        Exit Sub
    End If

    Set wb = Nothing
    On Error GoTo EH

    Set wb = Workbooks.Open(FileName:=sPath, ReadOnly:=True, UpdateLinks:=0, AddToMru:=False)

    ' 1) "초과근무수당 개인별 산출내역서" 제목이 있는 시트를 후보로 수집
    Set colCand = New Collection
    For Each ws In wb.Worksheets
        If SheetHasTitle(ws) Then colCand.Add ws
    Next ws

    If colCand.Count = 0 Then
        colLog.Add Array(sName, "", "", "", "", "", "", "", "", "산출내역서 시트 없음")
        GoTo CloseIt
    ElseIf colCand.Count = 1 Then
        Set wsT = colCand(1)
    Else
        ' 2) 후보가 여러 개면 시트명 규칙으로 하나를 고른다
        Set wsT = PickSheetByName(colCand)
        If wsT Is Nothing Then
            colLog.Add Array(sName, CandNames(colCand), "", "", "", "", "", "", "", _
                             "대상 시트 판별 실패 - 확인 필요")
            GoTo CloseIt
        End If
    End If

    ' 3) 시트에서 값 추출
    ScanSheet wsT, yr, mo, ship, dWork, dOT, nPer, sYmSrc

    ' 시트에서 못 찾은 것은 파일명 / 경로에서 보충한다
    If mo = 0 Then
        mo = MonthFromName(sName)
        If mo > 0 Then sYmSrc = AppendSrc(sYmSrc, "월:파일명")
    End If
    If yr = 0 Then
        yr = FindYear(sPath, True)
        If yr > 0 Then sYmSrc = AppendSrc(sYmSrc, "연:경로")
    End If

    If nPer = 0 Then
        colLog.Add Array(sName, wsT.Name, "", "", sYmSrc, ship, 0, 0, 0, "급여 세부내용 없음")
        GoTo CloseIt
    End If

    If yr = 0 Or mo = 0 Then
        colLog.Add Array(sName, wsT.Name, yr, mo, sYmSrc, ship, nPer, dWork, dOT, _
                         "연월 확인 필요 - 집계 제외")
        GoTo CloseIt
    End If

    ' 4) 같은 연월 + 같은 함정이 두 번 들어오면 중복으로 보고 제외
    sKey = Format$(yr, "0000") & "-" & Format$(mo, "00") & "|" & ship
    If dctSeen.Exists(sKey) Then
        colLog.Add Array(sName, wsT.Name, yr, mo, sYmSrc, ship, nPer, dWork, dOT, _
                         "중복 - 집계 제외 (" & dctSeen(sKey) & ")")
        GoTo CloseIt
    End If
    dctSeen.Add sKey, sName

    AddMonth dctMonth, yr, mo, dWork, dOT, nPer
    colLog.Add Array(sName, wsT.Name, yr, mo, sYmSrc, ship, nPer, dWork, dOT, "정상")

CloseIt:
    On Error Resume Next
    If Not wb Is Nothing Then wb.Close SaveChanges:=False
    On Error GoTo 0
    Exit Sub

EH:
    colLog.Add Array(sName, "", "", "", "", "", "", "", "", "오류 - " & Err.Description)
    On Error Resume Next
    If Not wb Is Nothing Then wb.Close SaveChanges:=False
End Sub


'==================================================================
' 시트에 "초과근무수당 개인별 산출내역서" 제목이 있는가
'==================================================================
Private Function SheetHasTitle(ws As Worksheet) As Boolean
    Dim v As Variant
    Dim r As Long, c As Long

    On Error Resume Next
    v = ws.Range(ws.Cells(1, 1), ws.Cells(HDR_ROWS, HDR_COLS)).Value
    On Error GoTo 0
    If Not IsArray(v) Then Exit Function

    For r = 1 To UBound(v, 1)
        For c = 1 To UBound(v, 2)
            If VarType(v(r, c)) = vbString Then
                If InStr(Norm(v(r, c)), K_TITLE) > 0 Then
                    SheetHasTitle = True
                    Exit Function
                End If
            End If
        Next c
    Next r
End Function


'==================================================================
' 후보 시트가 여러 개일 때 시트명 규칙으로 선택
'   - 공백 제거 후 "초과근무수당" 또는 "초간근무수당" 을 포함
'   - 단, "합계" 또는 "내역" 이 들어간 것은 제외
'   - 정확히 하나만 남을 때에만 채택
'==================================================================
Private Function PickSheetByName(colCand As Collection) As Worksheet
    Dim ws As Worksheet

    ' 1순위: 시트명에 "경비함정"
    Set ws = MatchOneSheet(colCand, 1)
    ' 2순위: "초과근무수당" / "초간근무수당" (합계, 내역 은 제외)
    If ws Is Nothing Then Set ws = MatchOneSheet(colCand, 2)

    Set PickSheetByName = ws
End Function


' 규칙에 맞는 시트가 정확히 하나일 때만 돌려준다
Private Function MatchOneSheet(colCand As Collection, ByVal nMode As Long) As Worksheet
    Dim ws As Worksheet, hit As Worksheet
    Dim n As Long

    For Each ws In colCand
        If SheetNameMatches(Norm(ws.Name), nMode) Then
            n = n + 1
            Set hit = ws
        End If
    Next ws

    If n = 1 Then Set MatchOneSheet = hit
End Function


Private Function SheetNameMatches(ByVal s As String, ByVal nMode As Long) As Boolean
    Select Case nMode
        Case 1
            SheetNameMatches = (InStr(s, "경비함정") > 0)
        Case 2
            If InStr(s, "초과근무수당") > 0 Or InStr(s, "초간근무수당") > 0 Then
                SheetNameMatches = (InStr(s, "합계") = 0 And InStr(s, "내역") = 0)
            End If
    End Select
End Function


Private Function CandNames(colCand As Collection) As String
    Dim ws As Worksheet, s As String
    For Each ws In colCand
        If Len(s) > 0 Then s = s & ", "
        s = s & ws.Name
    Next ws
    CandNames = s
End Function


'==================================================================
' 시트 1개에서 연월 / 함정 / 총 근무시간 / 시간외 / 인원수 추출
'==================================================================
Private Sub ScanSheet(ws As Worksheet, ByRef yr As Long, ByRef mo As Long, _
                      ByRef ship As String, ByRef dWork As Double, _
                      ByRef dOT As Double, ByRef nPer As Long, ByRef ymSrc As String)
    Dim v As Variant
    Dim nR As Long, nC As Long
    Dim r As Long, c As Long, rHdr As Long
    Dim s As String

    yr = 0: mo = 0: ship = "": dWork = 0: dOT = 0: nPer = 0: ymSrc = ""

    nR = ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1
    nC = ws.UsedRange.Column + ws.UsedRange.Columns.Count - 1
    If nR > MAX_ROWS Then nR = MAX_ROWS
    If nC > MAX_COLS Then nC = MAX_COLS
    If nR < 2 Then nR = 2
    If nC < 2 Then nC = 2

    On Error Resume Next
    v = ws.Range(ws.Cells(1, 1), ws.Cells(nR, nC)).Value
    On Error GoTo 0
    If Not IsArray(v) Then Exit Sub

    nR = UBound(v, 1)
    nC = UBound(v, 2)

    ' ---- 1) 머리글에서 연월 / 함정 ----
    ' 산정서마다 머리글 모양이 다르므로 아래 순서로 찾고, 어디서 찾았는지
    ' ymSrc 에 남겨 [처리내역] 시트에서 확인할 수 있게 한다.
    rHdr = HDR_ROWS
    If rHdr > nR Then rHdr = nR

    ' (1) "초과근무수당 일집계 현황(2025년 5월)"
    For r = 1 To rHdr
        For c = 1 To nC
            If VarType(v(r, c)) = vbString Then
                s = Norm(v(r, c))
                If Len(s) > 0 Then
                    If yr = 0 Then
                        If InStr(s, K_PERIOD) > 0 Then
                            ParseYM s, yr, mo
                            If yr > 0 Then ymSrc = "일집계현황"
                        End If
                    End If
                    If Len(ship) = 0 Then
                        If InStr(s, K_TITLE) > 0 Then ship = ParseParen(s)
                    End If
                End If
            End If
        Next c
    Next r

    ' (2) 머리글 어디서든 "____년 __월" 형태
    If yr = 0 Then
        For r = 1 To rHdr
            For c = 1 To nC
                If VarType(v(r, c)) = vbString Then
                    s = Norm(v(r, c))
                    If InStr(s, "년") > 0 And InStr(s, "월") > 0 Then
                        ParseYM s, yr, mo
                        If yr > 0 Then
                            ymSrc = "머리글(년월)"
                            Exit For
                        End If
                    End If
                End If
            Next c
            If yr > 0 Then Exit For
        Next r
    End If

    ' (3) 월: "1505함 5월 출동현황" 같은 머리글
    If mo = 0 Then
        mo = MonthInBlock(v, rHdr, nC)
        If mo > 0 Then ymSrc = AppendSrc(ymSrc, "월:머리글")
    End If

    ' (4) 연도: 머리글의 네 자리 연도 (예: 관련근거 "1505함-0494-2024-05-00152")
    If yr = 0 Then
        yr = YearInBlock(v, rHdr, nC)
        If yr > 0 Then ymSrc = AppendSrc(ymSrc, "연:머리글")
    End If

    ' (5) 월: 시트명  (예: "5월 초간근무수당")
    If mo = 0 Then
        mo = MonthFromName(ws.Name)
        If mo > 0 Then ymSrc = AppendSrc(ymSrc, "월:시트명")
    End If

    ' ---- 2) [급여 세부내용] 박스를 모두 찾아 합산 ----
    For r = 1 To nR
        For c = 1 To nC
            If VarType(v(r, c)) = vbString Then
                If InStr(Norm(v(r, c)), K_BOX) > 0 Then
                    nPer = nPer + 1
                    SumBox v, nR, nC, r, c, dWork, dOT
                End If
            End If
        Next c
    Next r
End Sub


'==================================================================
' [급여 세부내용] 박스 하나에서 총 근무시간 / 시간외 를 더한다
'
'   (r0,c0) [급여 세부내용        ]
'           [총 근무시간][총 복무규정시간]   <- 라벨
'           [    220    ][    120       ]   <- 값 (라벨 바로 아래)
'           [시간외(시간)][   100       ]   <- 라벨 + 값 (오른쪽)
'==================================================================
Private Sub SumBox(v As Variant, ByVal nR As Long, ByVal nC As Long, _
                   ByVal r0 As Long, ByVal c0 As Long, _
                   ByRef dWork As Double, ByRef dOT As Double)
    Dim r As Long, c As Long
    Dim rEnd As Long, cEnd As Long
    Dim s As String
    Dim bW As Boolean, bO As Boolean

    rEnd = r0 + BOX_DEPTH
    If rEnd > nR Then rEnd = nR
    cEnd = c0 + 2
    If cEnd > nC Then cEnd = nC

    For r = r0 + 1 To rEnd
        For c = c0 To cEnd
            If VarType(v(r, c)) = vbString Then
                s = Norm(v(r, c))
                If Not bW Then
                    If InStr(s, K_WORK) = 1 Then
                        ' 값은 라벨 바로 아래, 없으면 오른쪽
                        dWork = dWork + PickNum(v, nR, nC, r + 1, c, r, c + 1)
                        bW = True
                    End If
                End If
                If Not bO Then
                    If InStr(s, K_OT) = 1 Then
                        ' 값은 라벨 오른쪽, 없으면 아래
                        dOT = dOT + PickNum(v, nR, nC, r, c + 1, r + 1, c)
                        bO = True
                    End If
                End If
            End If
        Next c
        If bW And bO Then Exit For
    Next r
End Sub


Private Function PickNum(v As Variant, ByVal nR As Long, ByVal nC As Long, _
                         ByVal r1 As Long, ByVal c1 As Long, _
                         ByVal r2 As Long, ByVal c2 As Long) As Double
    Dim d As Double
    If TryNum(v, nR, nC, r1, c1, d) Then
        PickNum = d
    ElseIf TryNum(v, nR, nC, r2, c2, d) Then
        PickNum = d
    End If
End Function


Private Function TryNum(v As Variant, ByVal nR As Long, ByVal nC As Long, _
                        ByVal r As Long, ByVal c As Long, ByRef d As Double) As Boolean
    Dim s As String
    If r < 1 Or c < 1 Or r > nR Or c > nC Then Exit Function

    Select Case VarType(v(r, c))
        Case vbByte, vbInteger, vbLong, vbSingle, vbDouble, vbCurrency, vbDecimal
            d = CDbl(v(r, c))
            TryNum = True
        Case vbString
            s = Replace$(Norm(v(r, c)), ",", "")
            If Len(s) > 0 Then
                If IsNumeric(s) Then
                    d = CDbl(s)
                    TryNum = True
                End If
            End If
    End Select
End Function


'==================================================================
' 문자열 유틸
'==================================================================
Private Function Norm(ByVal vIn As Variant) As String
    Dim s As String
    If VarType(vIn) <> vbString Then Exit Function
    s = CStr(vIn)
    s = Replace$(s, " ", "")
    s = Replace$(s, vbTab, "")
    s = Replace$(s, vbCr, "")
    s = Replace$(s, vbLf, "")
    s = Replace$(s, ChrW$(&HA0), "")
    s = Replace$(s, ChrW$(&H3000), "")
    Norm = s
End Function


' "초과근무수당일집계현황(2025년5월)" -> yr=2025, mo=5
Private Sub ParseYM(ByVal s As String, ByRef yr As Long, ByRef mo As Long)
    Dim p As Long, q As Long
    Dim y As Long, m As Long

    p = InStr(s, "년")
    q = InStr(s, "월")
    If p = 0 Or q <= p Then Exit Sub

    y = TailDigits(Left$(s, p - 1))
    m = TailDigits(Mid$(s, p + 1, q - p - 1))

    If y >= 0 And y <= 99 Then y = 2000 + y
    If y < 1990 Or y > 2099 Then Exit Sub
    If m < 1 Or m > 12 Then Exit Sub

    yr = y
    mo = m
End Sub


 머리글에서 "__월" 을 찾는다. "현황" 이 함께 있는 칸을 우선한다.
Private Function MonthInBlock(v As Variant, ByVal rHdr As Long, ByVal nC As Long) As Long
    Dim r As Long, c As Long, m As Long, best As Long
    Dim s As String

    For r = 1 To rHdr
        For c = 1 To nC
            If VarType(v(r, c)) = vbString Then
                s = Norm(v(r, c))
                If InStr(s, "월") > 0 Then
                    m = MonthFromName(s)
                    If m > 0 Then
                        If InStr(s, "현황") > 0 Then
                            MonthInBlock = m
                            Exit Function
                        End If
                        If best = 0 Then best = m
                    End If
                End If
            End If
        Next c
    Next r

    MonthInBlock = best
End Function


' 머리글에서 네 자리 연도를 찾는다
Private Function YearInBlock(v As Variant, ByVal rHdr As Long, ByVal nC As Long) As Long
    Dim r As Long, c As Long, y As Long

    For r = 1 To rHdr
        For c = 1 To nC
            If VarType(v(r, c)) = vbString Then
                y = FindYear(CStr(v(r, c)), False)
                If y > 0 Then
                    YearInBlock = y
                    Exit Function
                End If
            End If
        Next c
    Next r
End Function


' 앞뒤가 숫자가 아닌 네 자리 2000~2099 를 찾는다.
' bFromRight 면 마지막 것을 돌려준다 (경로는 파일 쪽이 더 믿을 만하므로).
Private Function FindYear(ByVal s As String, ByVal bFromRight As Boolean) As Long
    Dim i As Long, n As Long, y As Long
    Dim t As String

    n = Len(s)
    If n < 4 Then Exit Function

    For i = 1 To n - 3
        t = Mid$(s, i, 4)
        If t Like "####" Then
            If i = 1 Or Not (Mid$(s, i - 1, 1) Like "#") Then
                If i + 4 > n Or Not (Mid$(s, i + 4, 1) Like "#") Then
                    y = CLng(t)
                    If y >= 2000 And y <= 2099 Then
                        FindYear = y
                        If Not bFromRight Then Exit Function
                    End If
                End If
            End If
        End If
    Next i
End Function


Private Function AppendSrc(ByVal s As String, ByVal sAdd As String) As String
    If Len(s) = 0 Then
        AppendSrc = sAdd
    Else
        AppendSrc = s & " + " & sAdd
    End If
End Function


' "5월 초간근무수당" -> 5
Private Function MonthFromName(ByVal sName As String) As Long
    Dim s As String
    Dim p As Long, m As Long
    s = Norm(sName)
    p = InStr(s, "월")
    If p = 0 Then Exit Function
    m = TailDigits(Left$(s, p - 1))
    If m >= 1 And m <= 12 Then MonthFromName = m
End Function


' 문자열 끝쪽의 연속된 숫자를 뽑는다
Private Function TailDigits(ByVal s As String) As Long
    Dim i As Long
    Dim t As String
    For i = Len(s) To 1 Step -1
        If Mid$(s, i, 1) Like "#" Then
            t = Mid$(s, i, 1) & t
        Else
            Exit For
        End If
    Next i
    If Len(t) > 0 And Len(t) <= 4 Then TailDigits = CLng(t)
End Function


' "...산출내역서(1505함)" -> "1505함"
Private Function ParseParen(ByVal s As String) As String
    Dim p As Long, q As Long
    p = InStrRev(s, "(")
    If p = 0 Then p = InStrRev(s, ChrW$(&HFF08))
    If p = 0 Then Exit Function
    q = InStr(p, s, ")")
    If q = 0 Then q = InStr(p, s, ChrW$(&HFF09))
    If q = 0 Then Exit Function
    If q - p - 1 <= 0 Then Exit Function
    ParseParen = Mid$(s, p + 1, q - p - 1)
End Function


'==================================================================
' 월별 누적
'==================================================================
Private Sub AddMonth(dct As Object, ByVal yr As Long, ByVal mo As Long, _
                     ByVal dWork As Double, ByVal dOT As Double, ByVal nPer As Long)
    Dim k As String
    Dim a As Variant

    k = Format$(yr, "0000") & Format$(mo, "00")
    If dct.Exists(k) Then
        a = dct(k)
        a(0) = a(0) + dWork
        a(1) = a(1) + dOT
        a(2) = a(2) + CDbl(nPer)
        dct(k) = a
    Else
        dct.Add k, Array(dWork, dOT, CDbl(nPer))
    End If
End Sub


'==================================================================
' 결과 시트 작성
'==================================================================
Private Sub WriteResult(dct As Object, colLog As Collection, ByVal nFile As Long)
    Dim ws As Worksheet, wsL As Worksheet
    Dim keys As Variant, tmp As Variant, a As Variant
    Dim i As Long, j As Long, r As Long, lastR As Long
    Dim k As String, curY As String
    Dim yrWork As Double, yrOT As Double, totWork As Double, totOT As Double
    Dim nOK As Long, nNG As Long

    Set ws = EnsureSheet(SH_RESULT)
    Set wsL = EnsureSheet(SH_LOG)

    ' ---- 이전 결과 지우기 (제목 / 버튼 영역은 보존) ----
    lastR = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastR < HDR_ROW Then lastR = HDR_ROW
    With ws.Range(ws.Cells(HDR_ROW - 2, 1), ws.Cells(lastR + 5, 8))
        .UnMerge
        .Clear
    End With

    ' ---- 안내 줄 ----
    With ws.Cells(HDR_ROW - 2, 1)
        .Value = "집계 일시 : " & Format$(Now, "yyyy-mm-dd hh:nn") & _
                 "      대상 파일 : " & nFile & "개"
        .Font.Size = 9
        .Font.Color = RGB(90, 90, 90)
    End With

    ' ---- 표 머리글 ----
    r = HDR_ROW
    ws.Cells(r, 1).Value = "연도"
    ws.Cells(r, 2).Value = "월"
    ws.Cells(r, 3).Value = "총 근무시간"
    ws.Cells(r, 4).Value = "시간외(시간)"
    With ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Interior.Color = RGB(221, 235, 247)
        .RowHeight = 20
    End With
    DrawBorder ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))
    r = r + 1

    If dct.Count = 0 Then
        ws.Cells(r, 1).Value = "집계된 자료가 없습니다. [처리내역] 시트를 확인하세요."
        ws.Range(ws.Cells(r, 1), ws.Cells(r, 4)).Merge
        WriteLog wsL, colLog, nOK, nNG
        FinishUp ws, nFile, nOK, nNG
        Exit Sub
    End If

    ' ---- 연월 키 정렬 (YYYYMM 문자열이므로 사전순 = 시간순) ----
    keys = dct.Keys
    For i = LBound(keys) To UBound(keys) - 1
        For j = i + 1 To UBound(keys)
            If CStr(keys(j)) < CStr(keys(i)) Then
                tmp = keys(i): keys(i) = keys(j): keys(j) = tmp
            End If
        Next j
    Next i

    ' ---- 월별 행 + 연도 소계 ----
    curY = ""
    For i = LBound(keys) To UBound(keys)
        k = CStr(keys(i))
        a = dct(k)

        If Len(curY) > 0 And curY <> Left$(k, 4) Then
            WriteSubtotal ws, r, curY, yrWork, yrOT
            r = r + 1
            yrWork = 0: yrOT = 0
        End If
        curY = Left$(k, 4)

        ws.Cells(r, 1).Value = CLng(Left$(k, 4))
        ws.Cells(r, 2).Value = CLng(Mid$(k, 5, 2)) & "월"
        ws.Cells(r, 3).Value = a(0)
        ws.Cells(r, 4).Value = a(1)
        ws.Range(ws.Cells(r, 1), ws.Cells(r, 2)).HorizontalAlignment = xlCenter
        DrawBorder ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))

        yrWork = yrWork + a(0): yrOT = yrOT + a(1)
        totWork = totWork + a(0): totOT = totOT + a(1)
        r = r + 1
    Next i

    WriteSubtotal ws, r, curY, yrWork, yrOT
    r = r + 1

    ' ---- 총 합계 ----
    With ws.Range(ws.Cells(r, 1), ws.Cells(r, 2))
        .Merge
        .Value = "총 합계"
        .HorizontalAlignment = xlCenter
    End With
    ws.Cells(r, 3).Value = totWork
    ws.Cells(r, 4).Value = totOT
    With ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))
        .Font.Bold = True
        .Interior.Color = RGB(252, 228, 214)
        .RowHeight = 22
    End With
    DrawBorder ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))
    ws.Range(ws.Cells(r, 1), ws.Cells(r, 4)).Borders(xlEdgeBottom).LineStyle = xlDouble

    ' ---- 숫자 서식 / 열 너비 ----
    ws.Range(ws.Cells(HDR_ROW + 1, 3), ws.Cells(r, 4)).NumberFormat = "#,##0.0"
    ws.Columns("A").ColumnWidth = 10
    ws.Columns("B").ColumnWidth = 10
    ws.Columns("C").ColumnWidth = 16
    ws.Columns("D").ColumnWidth = 16

    WriteLog wsL, colLog, nOK, nNG
    FinishUp ws, nFile, nOK, nNG
End Sub


Private Sub WriteSubtotal(ws As Worksheet, ByVal r As Long, ByVal sYear As String, _
                          ByVal dSumWork As Double, ByVal dSumOT As Double)
    With ws.Range(ws.Cells(r, 1), ws.Cells(r, 2))
        .Merge
        .Value = sYear & "년 합계"
        .HorizontalAlignment = xlCenter
    End With
    ws.Cells(r, 3).Value = dSumWork
    ws.Cells(r, 4).Value = dSumOT
    With ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))
        .Font.Bold = True
        .Interior.Color = RGB(237, 237, 237)
    End With
    DrawBorder ws.Range(ws.Cells(r, 1), ws.Cells(r, 4))
End Sub


Private Sub DrawBorder(rg As Range)
    Dim i As Long
    For i = 7 To 10          ' xlEdgeLeft, xlEdgeTop, xlEdgeBottom, xlEdgeRight
        With rg.Borders(i)
            .LineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(160, 160, 160)
        End With
    Next i
    With rg.Borders(xlInsideVertical)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = RGB(160, 160, 160)
    End With
End Sub


'==================================================================
' 처리내역 시트
'==================================================================
Private Sub WriteLog(wsL As Worksheet, colLog As Collection, _
                     ByRef nOK As Long, ByRef nNG As Long)
    Dim i As Long, c As Long, r As Long, lastR As Long
    Dim a As Variant
    Dim hdr As Variant

    hdr = Array("파일명", "시트명", "연도", "월", "연월 출처", "함정", "인원수", _
                "총 근무시간", "시간외(시간)", "상태")

    lastR = wsL.Cells(wsL.Rows.Count, 1).End(xlUp).Row
    If lastR < 1 Then lastR = 1
    wsL.Range(wsL.Cells(1, 1), wsL.Cells(lastR + 5, 10)).Clear

    For c = 0 To UBound(hdr)
        wsL.Cells(1, c + 1).Value = hdr(c)
    Next c
    With wsL.Range(wsL.Cells(1, 1), wsL.Cells(1, 10))
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .Interior.Color = RGB(221, 235, 247)
    End With
    DrawBorder wsL.Range(wsL.Cells(1, 1), wsL.Cells(1, 10))

    r = 2
    For i = 1 To colLog.Count
        a = colLog(i)
        For c = 0 To 9
            wsL.Cells(r, c + 1).Value = a(c)
        Next c
        If a(9) = "정상" Then
            nOK = nOK + 1
        Else
            nNG = nNG + 1
            wsL.Cells(r, 10).Font.Color = RGB(192, 0, 0)
        End If
        DrawBorder wsL.Range(wsL.Cells(r, 1), wsL.Cells(r, 10))
        r = r + 1
    Next i

    If r > 2 Then
        wsL.Range(wsL.Cells(2, 8), wsL.Cells(r - 1, 9)).NumberFormat = "#,##0.0"
    End If

    wsL.Columns("A").ColumnWidth = 42
    wsL.Columns("B").ColumnWidth = 22
    wsL.Columns("C:D").ColumnWidth = 8
    wsL.Columns("E").ColumnWidth = 16
    wsL.Columns("F").ColumnWidth = 10
    wsL.Columns("G").ColumnWidth = 8
    wsL.Columns("H:I").ColumnWidth = 14
    wsL.Columns("J").ColumnWidth = 34
End Sub


Private Sub FinishUp(ws As Worksheet, ByVal nFile As Long, _
                     ByVal nOK As Long, ByVal nNG As Long)
    Dim s As String
    On Error Resume Next
    ws.Activate
    ws.Range("A1").Select
    On Error GoTo 0

    s = "집계가 끝났습니다." & vbCrLf & vbCrLf & _
        "선택한 파일 : " & nFile & "개" & vbCrLf & _
        "정상 처리   : " & nOK & "개"
    If nNG > 0 Then
        s = s & vbCrLf & "확인 필요   : " & nNG & "개" & vbCrLf & vbCrLf & _
                "[처리내역] 시트에서 사유를 확인하세요."
    End If
    MsgBox s, vbInformation, "초과근무수당 집계"
End Sub


Private Function EnsureSheet(ByVal sName As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sName)
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add( _
                 After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = sName
    End If
    Set EnsureSheet = ws
End Function
