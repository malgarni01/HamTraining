{ ===========================================================================
  BACKPROC.PAS additions — DARPA CoasterChase MED-PC integration
  ---------------------------------------------------------------------------
  Plan: Manuals/MED-PC_Integration_Plan.pdf  Section 4.2
  Pascal API verbatim source: DOC-301 App. C "Background Procedures"
  p.211-215 and App. D "Internal Data Structures" p.217+.

  HOW TO DEPLOY (see medpc/MED-PC_DEPLOYMENT.md):
    1. Back up the stock C:\MED-PC\BACKPROC.PAS.
    2. Replace the bodies of the stock BackProc1 and BackProc2 with the two
       procedures below (keep that file's existing unit header / `uses`
       clause; the stock examples already pull in SysUtils, which is all
       these procedures need: FindFirst/FindNext/FindClose, ExtractFileExt,
       FileExists, DeleteFile, RenameFile, Format, Val, Trim, LowerCase).
       If you prefer, drop these in verbatim and confirm the unit compiles.
    3. Recompile by running TRANS  Translation | Batch Translate!  on any
       .mpc — MED-PC auto-recompiles BACKPROC.PAS when it has changed
       (DOC-301 p.215; there is no separate compiler command).

  Procedure contract MUST be exactly (DOC-301 p.211, verbatim):
       Procedure BackProcN(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
  and the LAST executed line MUST be  BackRequest[Box][N] := False;
  where N equals the BKGRND number (1 or 2). Only MPCGlobal and Box are
  passed; everything else crosses via MSN variables.

  MSN variable contract (see medpc/CoasterChase.mpc):
    BackProc1 (BKGRND 1, "scan trigger dir") sets:
        R := reward_size      (>=1)
        S := seq              (numeric)
        Q := 1                (dispense request pending)
        E := 1                (on cmd=stop; MSN then STOPSAVEs)
        D := 1                (handshake: this proc has finished)
      and answers heartbeat/stop acks directly.
    BackProc2 (BKGRND 2, "write ack") reads S, R, P, T and writes the
        per-request .ack, then sets D := 1.

  Variable access syntax is verbatim DOC-301 App. C/D:
        read :   x := BigArr[Vars['S'].StartOffset];
        write:   BigArr[Vars['Q'].StartOffset] := 1;

  IPC layout (local disk only, exclude from antivirus — plan Section 9):
        C:\MED-PC\CoasterChase\trigger\   Python writes <seq>.req
        C:\MED-PC\CoasterChase\ack\       this code writes <seq>.ack
  Files use one key=value per line (newline-delimited) so Pascal Readln
  parses each field on its own line — see MED-PC_DEPLOYMENT.md "Wire format".
  =========================================================================== }


Procedure BackProc1(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
Const
   TrigDir = 'C:\MED-PC\CoasterChase\trigger\';
   AckDir  = 'C:\MED-PC\CoasterChase\ack\';
Var
   Data       : ^DataRec;
   Sr         : TSearchRec;
   FindRc     : Integer;
   MinName    : String;
   FullName   : String;
   Cmd        : String;
   Ln         : String;
   Key, Vl    : String;
   EqPos      : Integer;
   InF        : Text;
   RewardSize : LongInt;
   SeqNo      : LongInt;
   VErr       : Integer;

   { nested helper: write <AckName>.ack atomically (tmp then rename) }
   Procedure PutAck(Const AckName, Status: String; Req, Del, Ems: LongInt);
   Var Tmp, Fin: String; OutF: Text;
   Begin
      Tmp := AckDir + AckName + '.ack.tmp';
      Fin := AckDir + AckName + '.ack';
      AssignFile(OutF, Tmp);
      {$I-} Rewrite(OutF); {$I+}
      If IORESULT = 0 Then
      Begin
         Writeln(OutF, 'seq=' + AckName);
         Writeln(OutF, 'status=' + Status);
         Writeln(OutF, 'pellets_requested=' + IntToStr(Req));
         Writeln(OutF, 'pellets_delivered=' + IntToStr(Del));
         Writeln(OutF, 'elapsed_ms=' + IntToStr(Ems));
         Close(OutF);
         DeleteFile(Fin);            { RenameFile fails if target exists }
         RenameFile(Tmp, Fin);
      End;
   End;

Begin
   With MPCGlobal^ Do
   Begin
      Data := BoxPointer[Box];
      With Data^, Data^.Description, Data^.Header Do
      Begin

         { ---- 1. heartbeat: answer immediately so it is never starved --- }
         If FileExists(TrigDir + 'heartbeat.req') Then
         Begin
            PutAck('heartbeat', 'alive', 0, 0, 0);
            DeleteFile(TrigDir + 'heartbeat.req');
         End;

         { ---- 2. oldest = lexicographically smallest *.req (not .tmp) --- }
         MinName := '';
         FindRc := FindFirst(TrigDir + '*.req', faAnyFile, Sr);
         While FindRc = 0 Do
         Begin
            If ((Sr.Attr And faDirectory) = 0)
               And (LowerCase(ExtractFileExt(Sr.Name)) = '.req')
               And (Pos('.tmp', LowerCase(Sr.Name)) = 0)
               And (LowerCase(Sr.Name) <> 'heartbeat.req') Then
               If (MinName = '') Or (Sr.Name < MinName) Then
                  MinName := Sr.Name;
            FindRc := FindNext(Sr);
         End;
         FindClose(Sr);

         If MinName <> '' Then
         Begin
            FullName   := TrigDir + MinName;
            Cmd        := '';
            RewardSize := 1;
            SeqNo      := 0;

            { ---- 3. parse one key=value per line ----------------------- }
            AssignFile(InF, FullName);
            {$I-} Reset(InF); {$I+}
            If IORESULT = 0 Then
            Begin
               While Not Eof(InF) Do
               Begin
                  Readln(InF, Ln);
                  Ln    := Trim(Ln);
                  EqPos := Pos('=', Ln);
                  If EqPos > 0 Then
                  Begin
                     Key := Trim(Copy(Ln, 1, EqPos - 1));
                     Vl  := Trim(Copy(Ln, EqPos + 1, Length(Ln)));
                     If Key = 'cmd' Then
                        Cmd := LowerCase(Vl);
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
                  End;
               End;
               Close(InF);
            End;

            { ---- 4. act on the command -------------------------------- }
            If Cmd = 'stop' Then
            Begin
               PutAck(Format('%.6d', [SeqNo]), 'stopped', 0, 0, 0);
               BigArr[Vars['E'].StartOffset] := 1;   { MSN -> STOPSAVE }
            End
            Else
            Begin                                    { default: dispense }
               BigArr[Vars['R'].StartOffset] := RewardSize;
               BigArr[Vars['S'].StartOffset] := SeqNo;
               BigArr[Vars['Q'].StartOffset] := 1;
            End;

            DeleteFile(FullName);
         End;

         BigArr[Vars['D'].StartOffset] := 1;          { handshake done }
      End; {With Data^...}

      VErr := IORESULT;                               { clear I/O errors }
      BackRequest[Box][1] := False;                   { MANDATORY (proc 1) }
   End; {With MPCGlobal^}
End; {BackProc1}


Procedure BackProc2(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
Const
   AckDir = 'C:\MED-PC\CoasterChase\ack\';
Var
   Data   : ^DataRec;
   SeqNo  : LongInt;
   ReqN   : LongInt;
   DelN   : LongInt;
   Ems    : LongInt;
   Status : String;
   Base   : String;
   Tmp    : String;
   Fin    : String;
   OutF   : Text;
   VErr   : Integer;
Begin
   With MPCGlobal^ Do
   Begin
      Data := BoxPointer[Box];
      With Data^, Data^.Description, Data^.Header Do
      Begin
         SeqNo := Trunc(BigArr[Vars['S'].StartOffset]);
         ReqN  := Trunc(BigArr[Vars['R'].StartOffset]);
         DelN  := Trunc(BigArr[Vars['P'].StartOffset]);
         Ems   := Round(BigArr[Vars['T'].StartOffset] * 1000);

         If DelN >= ReqN Then Status := 'ok'
         Else If DelN > 0 Then Status := 'partial'
         Else Status := 'empty';

         Base := Format('%.6d', [SeqNo]);
         Tmp  := AckDir + Base + '.ack.tmp';
         Fin  := AckDir + Base + '.ack';

         AssignFile(OutF, Tmp);
         {$I-} Rewrite(OutF); {$I+}
         If IORESULT = 0 Then
         Begin
            Writeln(OutF, 'seq=' + Base);
            Writeln(OutF, 'status=' + Status);
            Writeln(OutF, 'pellets_requested=' + IntToStr(ReqN));
            Writeln(OutF, 'pellets_delivered=' + IntToStr(DelN));
            Writeln(OutF, 'elapsed_ms=' + IntToStr(Ems));
            Close(OutF);
            DeleteFile(Fin);            { RenameFile fails if target exists }
            RenameFile(Tmp, Fin);
         End;

         BigArr[Vars['D'].StartOffset] := 1;          { handshake done }
      End; {With Data^...}

      VErr := IORESULT;                               { clear I/O errors }
      BackRequest[Box][2] := False;                   { MANDATORY (proc 2) }
   End; {With MPCGlobal^}
End; {BackProc2}
