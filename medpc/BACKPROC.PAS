{ ===========================================================================
  BACKPROC.PAS additions — DARPA CoasterChase MED-PC integration
  ---------------------------------------------------------------------------
  Plan: Manuals/MED-PC_Integration_Plan.pdf  Section 4.2
  Pascal API verbatim source: DOC-301 App. C "Background Procedures"
  p.211-215 and App. D "Internal Data Structures" p.217+.

  IPC PROTOCOL (Option B, fixed filenames -- empirically chosen 2026-05-20):
    The plan originally specified zero-padded per-sequence filenames
    (000042.req etc.) scanned via SysUtils.FindFirst. On the COM-106 the
    bundled Pascal compiler refused that overload ("Got 'TRawbyteSearchRec',
    expected 'QWord'" -- another FindFirst from the stock unit's scope
    shadows the SysUtils one). Step 8.7 proved the fixed-name path works,
    so production uses two fixed slots:
        trigger\request.req     <- Python writes a single pending request
        ack    \request.ack     <- this code writes the matching reply
        trigger\heartbeat.req   <- Python writes liveness ping
        ack    \heartbeat.ack   <- this code writes 'alive' reply
    The Python side enforces "no second request before reading the prior
    ack" (plan Section 9 "No re-entrancy"), so a single fixed slot is
    sufficient. The seq number is carried INSIDE the file contents so
    Python can still cross-check that an ack matches the request it sent.

  HOW TO DEPLOY (see medpc/MED-PC_DEPLOYMENT.md):
    1. Back up the stock C:\MED-PC\BACKPROC.PAS.
    2. Replace the bodies of the stock BackProc1 and BackProc2 with the two
       procedures below (keep that file's existing unit header / `uses`
       clause; the stock examples already pull in SysUtils, which is all
       these procedures need: Trim, LowerCase, Pos, Copy, Length, Val,
       IntToStr, DeleteFile, RenameFile).  No FindFirst / TSearchRec.
       NOTE: the stock unit also pulls in `Windows`, whose DeleteFile and
       RenameFile take PChar (LPCSTR) and shadow the SysUtils overloads
       (Backproc.pas error "Got 'AnsiString', expected 'PChar'"). All
       filename arguments below are wrapped in PChar(...) casts so the
       call matches either Windows.* or SysUtils.* regardless of which
       the compiler picks; the Pascal AnsiString → PChar cast is the
       documented idiom.
       If you prefer, drop these in verbatim and confirm the unit compiles.
    3. Recompile by opening a .mpc and running
          Translation | Batch Translate!
       MED-PC auto-recompiles BACKPROC.PAS when it has changed
       (DOC-301 p.215; there is no separate compiler command).

  Procedure contract MUST be exactly (DOC-301 p.211, verbatim):
       Procedure BackProcN(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
  and the LAST executed line MUST be  BackRequest[Box][N] := False;
  where N equals the BKGRND number (1 or 2). Only MPCGlobal and Box are
  passed; everything else crosses via MSN variables.

  MSN variable contract (see medpc/CoasterChase.mpc):
    BackProc1 (BKGRND 1, "consume the request slot") sets:
        R := reward_size      (>=1)
        S := seq              (numeric)
        Q := 1                (dispense request pending)
        E := 1                (on cmd=stop; MSN then STOPSAVEs)
        D := 1                (handshake: this proc has finished)
      and answers heartbeat / stop acks directly.
    BackProc2 (BKGRND 2, "write dispense ack") reads S, R, P, T and writes
        ack\request.ack, then sets D := 1.

  Variable access syntax is verbatim DOC-301 App. C/D:
        read :   x := BigArr[Vars['S'].StartOffset];
        write:   BigArr[Vars['Q'].StartOffset] := 1;

  IPC layout (local disk only, exclude from antivirus -- plan Section 9):
        C:\MED-PC\CoasterChase\trigger\   Python writes  request.req
                                                         heartbeat.req
        C:\MED-PC\CoasterChase\ack\       this code writes  request.ack
                                                            heartbeat.ack
  Files use one key=value per line (newline-delimited) so Pascal Readln
  parses each field on its own line -- see MED-PC_DEPLOYMENT.md "Wire format".
  =========================================================================== }


Procedure BackProc1(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
Const
   TrigDir = 'C:\MED-PC\CoasterChase\trigger\';
   AckDir  = 'C:\MED-PC\CoasterChase\ack\';
   ReqName = 'request';
   HbName  = 'heartbeat';
Var
   Data       : ^DataRec;
   Ln         : String;
   Cmd        : String;
   Key, Vl    : String;
   EqPos      : Integer;
   InF        : Text;
   RewardSize : LongInt;
   SeqNo      : LongInt;
   VErr       : Integer;

   { nested helper: write <AckBase>.ack atomically (tmp then rename).
     SeqText is what goes into the file's "seq=" line; for heartbeat it
     is the literal string 'heartbeat', for everything else it is the
     numeric seq formatted with IntToStr. }
   Procedure PutAck(Const AckBase, SeqText, Status: String;
                    Req, Del, Ems: LongInt);
   Var Tmp, Fin: String; OutF: Text;
   Begin
      Tmp := AckDir + AckBase + '.ack.tmp';
      Fin := AckDir + AckBase + '.ack';
      AssignFile(OutF, Tmp);
      {$I-} Rewrite(OutF); {$I+}
      If IORESULT = 0 Then
      Begin
         Writeln(OutF, 'seq=' + SeqText);
         Writeln(OutF, 'status=' + Status);
         Writeln(OutF, 'pellets_requested=' + IntToStr(Req));
         Writeln(OutF, 'pellets_delivered=' + IntToStr(Del));
         Writeln(OutF, 'elapsed_ms=' + IntToStr(Ems));
         Close(OutF);
         DeleteFile(PChar(Fin));     { RenameFile fails if target exists }
         RenameFile(PChar(Tmp), PChar(Fin));
      End;
   End;

Begin
   With MPCGlobal^ Do
   Begin
      Data := BoxPointer[Box];
      With Data^, Data^.Description, Data^.Header Do
      Begin

         { ---- 1. heartbeat: answer immediately so it is never starved --- }
         { DeleteFile returns True iff the file existed and was removed;   }
         { this is the existence check without needing FileExists.         }
         If DeleteFile(PChar(TrigDir + HbName + '.req')) Then
            PutAck(HbName, 'heartbeat', 'alive', 0, 0, 0);

         { ---- 2. open the single fixed dispense/stop request slot ------- }
         AssignFile(InF, TrigDir + ReqName + '.req');
         {$I-} Reset(InF); {$I+}
         If IORESULT = 0 Then
         Begin
            Cmd        := '';
            RewardSize := 1;
            SeqNo      := 0;

            { ---- parse one key=value per line ---------------------- }
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

            { ---- act on the command -------------------------------- }
            If Cmd = 'stop' Then
            Begin
               PutAck(ReqName, IntToStr(SeqNo), 'stopped', 0, 0, 0);
               BigArr[Vars['E'].StartOffset] := 1;   { MSN -> STOPSAVE }
            End
            Else
            Begin                                    { default: dispense }
               BigArr[Vars['R'].StartOffset] := RewardSize;
               BigArr[Vars['S'].StartOffset] := SeqNo;
               BigArr[Vars['Q'].StartOffset] := 1;
            End;

            DeleteFile(PChar(TrigDir + ReqName + '.req'));
         End;

         BigArr[Vars['D'].StartOffset] := 1;          { handshake done }
      End; {With Data^...}

      VErr := IORESULT;                               { clear I/O errors }
      BackRequest[Box][1] := False;                   { MANDATORY (proc 1) }
   End; {With MPCGlobal^}
End; {BackProc1}


Procedure BackProc2(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
Const
   AckDir  = 'C:\MED-PC\CoasterChase\ack\';
   AckBase = 'request';
Var
   Data   : ^DataRec;
   SeqNo  : LongInt;
   ReqN   : LongInt;
   DelN   : LongInt;
   Ems    : LongInt;
   Status : String;
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

         Tmp := AckDir + AckBase + '.ack.tmp';
         Fin := AckDir + AckBase + '.ack';

         AssignFile(OutF, Tmp);
         {$I-} Rewrite(OutF); {$I+}
         If IORESULT = 0 Then
         Begin
            Writeln(OutF, 'seq=' + IntToStr(SeqNo));
            Writeln(OutF, 'status=' + Status);
            Writeln(OutF, 'pellets_requested=' + IntToStr(ReqN));
            Writeln(OutF, 'pellets_delivered=' + IntToStr(DelN));
            Writeln(OutF, 'elapsed_ms=' + IntToStr(Ems));
            Close(OutF);
            DeleteFile(PChar(Fin));     { RenameFile fails if target exists }
            RenameFile(PChar(Tmp), PChar(Fin));
         End;

         BigArr[Vars['D'].StartOffset] := 1;          { handshake done }
      End; {With Data^...}

      VErr := IORESULT;                               { clear I/O errors }
      BackRequest[Box][2] := False;                   { MANDATORY (proc 2) }
   End; {With MPCGlobal^}
End; {BackProc2}
