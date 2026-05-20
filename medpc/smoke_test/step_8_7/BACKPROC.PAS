{ ===========================================================================
  BACKPROC.PAS  --  STEP 8.7 SMOKE TEST  (NOT the production file)
  ---------------------------------------------------------------------------
  Plan : Manuals/MED-PC_Integration_Plan.pdf  Section 8 step 7
         "File-drop round trip -- manual.  Expand BackProc1 to read
          trigger\test.req, log its contents to MED-PC's screen via SHOW.
          Drop a hand-crafted .req file with a text editor.  Confirms
          file I/O permissions and parse logic."

  PRE-REQUISITE: step 8.6 must already have passed on this COM-106.
                 (See medpc/smoke_test/BACKPROC.PAS for the step-8.6 version.)

  HISTORY NOTE
  ------------
  The first revision of this file used SysUtils.FindFirst to enumerate
  trigger\*.req . That failed to compile in MED-PC's bundled Pascal with
  "Backproc.pas(N,22) Error: Incompatible type for arg no. 1: Got
  'TRawbyteSearchRec', expected 'QWord'" -- another FindFirst overload
  in the stock unit's scope (likely a Win32 HANDLE-style API) is being
  preferred over SysUtils.FindFirst. We will solve that for the production
  scanner separately (likely by qualifying as SysUtils.FindFirst or by
  switching to a different enumeration primitive). For step 8.7, the plan
  text actually only requires reading one FIXED filename -- "test.req" --
  so this revision drops FindFirst entirely and tests just the file open
  + key=value parse path on that fixed name.

  What this DOES:
    BackProc1 -- on every invocation, tries to open
                       C:\MED-PC\CoasterChase\trigger\test.req
                 If the open succeeds, parses one key=value per line for:
                       cmd          (text, ignored here -- step 8.8 uses)
                       reward_size  (integer, default 1)
                       seq          (integer, default 0)
                 writes the parsed integers into MSN scalars R and S,
                 raises Q := 1 ("a file was read this pass"),
                 deletes the .req, sets handshake D := 1, returns.
                 If the open fails (no file, or file locked by editor),
                 just sets D := 1 and Q stays 0.

    BackProc2 -- minimal handshake stub (sets D := 1, clears BackRequest).
                 Not exercised by this MSN; defined only so the unit
                 still compiles cleanly.

  What this DOES NOT do:
    No .ack file is written.  No directory enumeration (no FindFirst).
    No MSN dispense state machine is touched.  No heartbeat handling.

  REQUIRED ONE-TIME SETUP (do this BEFORE Batch Translate!):
    Create the IPC directories on the COM-106 (PowerShell or Explorer):
        mkdir C:\MED-PC\CoasterChase\trigger
        mkdir C:\MED-PC\CoasterChase\ack
    If Windows Defender is real-time scanning, add an exclusion for
    C:\MED-PC\CoasterChase\  (plan Section 9).

  DEPLOY:
    1. Restore the stock C:\MED-PC\BACKPROC.PAS from the backup made
       before step 8.6, OR just replace BackProc1 / BackProc2 bodies
       again with the two procedures below.
    2. KEEP the stock unit header + `uses` clause untouched.  This
       version of BackProc1 needs only: AssignFile/Reset/Close/Readln/
       Eof/IORESULT/DeleteFile/Trim/LowerCase/Pos/Copy/Length/Val .
       All of those compiled fine in step 8.6's context.
    3. Open Step8_7.mpc in MED-PC and run
          Translation | Batch Translate!
       Compile log MUST show 0 translator errors AND BACKPROC.PAS being
       recompiled (a "compiling backproc.pas" line, or similar).
    4. Load Box 1 with Step8_7:    L;1;0;0;0;Step8_7    then   S;1

  TEST PROCEDURE:
    (a) Confirm field 1 "Files read F" starts at 0 and field 4 "Idle polls"
        increments steadily (proves BKGRND is running with no test.req
        present).
    (b) In Notepad, create a file with this exact content (3 lines, ANSI
        or UTF-8 NO BOM -- *not* UTF-16):
            cmd=dispense
            reward_size=5
            seq=42
        Save As (ANSI encoding):
            C:\MED-PC\CoasterChase\trigger\test.req
        WARNING: do NOT save with PowerShell `Out-File` (UTF-16 LE BOM
                 by default in PS 5.1).  Use Notepad (Save As -> ANSI)
                 or  Set-Content -Encoding ascii .
    (c) Within ~0.5 s, expect:
          - the file disappears from disk (Pascal deleted it)
          - field 1 "Files read F" -> 1
          - field 2 "Last reward_size R" -> 5
          - field 3 "Last seq S" -> 42
    (d) Drop another test.req with different reward_size/seq values to
        confirm the displayed values update.
    (e) PASS criterion: F == number of files you dropped, R and S match
        the LAST file dropped, no test.req left behind on disk.

  REVERT after step 8.7 passes: restore the stock BACKPROC.PAS (or move
    on to deploying medpc/BACKPROC.PAS for the full integration) and
    re-run Batch Translate!.

  Procedure contract (DOC-301 p.211, verbatim):
       Procedure BackProcN(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
  Last executed line MUST be   BackRequest[Box][N] := False;
  =========================================================================== }


Procedure BackProc1(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
Const
   TestFile = 'C:\MED-PC\CoasterChase\trigger\test.req';
Var
   Data       : ^DataRec;
   Ln         : String;
   Key, Vl    : String;
   EqPos      : Integer;
   InF        : Text;
   RewardSize : LongInt;
   SeqNo      : LongInt;
   VErr       : Integer;
Begin
   With MPCGlobal^ Do
   Begin
      Data := BoxPointer[Box];
      With Data^, Data^.Description, Data^.Header Do
      Begin

         RewardSize := 1;
         SeqNo      := 0;

         { ---- attempt to open the fixed test.req -------------------- }
         AssignFile(InF, TestFile);
         {$I-} Reset(InF); {$I+}
         If IORESULT = 0 Then
         Begin
            { ---- parse one key=value per line ----------------------- }
            While Not Eof(InF) Do
            Begin
               Readln(InF, Ln);
               Ln    := Trim(Ln);
               EqPos := Pos('=', Ln);
               If EqPos > 0 Then
               Begin
                  Key := Trim(Copy(Ln, 1, EqPos - 1));
                  Vl  := Trim(Copy(Ln, EqPos + 1, Length(Ln)));
                  If Key = 'reward_size' Then
                  Begin
                     Val(Vl, RewardSize, VErr);
                     If (VErr <> 0) Or (RewardSize < 1) Then
                        RewardSize := 1;
                  End;
                  If Key = 'seq' Then
                  Begin
                     Val(Vl, SeqNo, VErr);
                     If VErr <> 0 Then SeqNo := 0;
                  End;
                  { 'cmd' is parsed by production code but ignored here. }
               End;
            End;
            Close(InF);

            { ---- publish results to MSN; raise Q -------------------- }
            BigArr[Vars['R'].StartOffset] := RewardSize;
            BigArr[Vars['S'].StartOffset] := SeqNo;
            BigArr[Vars['Q'].StartOffset] := 1;

            DeleteFile(TestFile);            { consume the .req }
         End;

         BigArr[Vars['D'].StartOffset] := 1;  { handshake done }
      End; {With Data^...}

      VErr := IORESULT;                       { clear any pending I/O error }
      BackRequest[Box][1] := False;           { MANDATORY (proc 1) }
   End; {With MPCGlobal^}
End; {BackProc1}


Procedure BackProc2(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
Var
   Data : ^DataRec;
Begin
   With MPCGlobal^ Do
   Begin
      Data := BoxPointer[Box];
      With Data^, Data^.Description, Data^.Header Do
      Begin
         BigArr[Vars['D'].StartOffset] := 1;          { handshake done }
      End;
      BackRequest[Box][2] := False;                   { MANDATORY (proc 2) }
   End;
End; {BackProc2}
