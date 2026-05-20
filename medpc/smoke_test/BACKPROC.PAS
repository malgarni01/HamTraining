{ ===========================================================================
  BACKPROC.PAS  --  STEP 8.6 SMOKE TEST  (NOT the production file)
  ---------------------------------------------------------------------------
  Plan : Manuals/MED-PC_Integration_Plan.pdf  Section 8 step 6
         "Add a trivial BackProc1 that just sets D := 1 and
          BackRequest[Box][1] := False;. Call from MSN. Confirms the
          Pascal compile and BKGRND wiring."

  Purpose: answer Section 10 open questions #1 and #2 (does the COM-106
           have the Pascal toolchain wired up? does TRANS Batch Translate
           actually recompile BACKPROC.PAS?) BEFORE deploying the real
           production medpc/BACKPROC.PAS.

  What this DOES:
    BackProc1 -- sets D := 1, clears BackRequest[Box][1]. Nothing else.
    BackProc2 -- sets D := 1, clears BackRequest[Box][2]. Nothing else.
                 (Defined only so the stock unit still compiles if the
                 surrounding code references BackProc2.)

  What this DOES NOT do:
    No file I/O.  No trigger\ directory access.  No parsing.
    No reliance on the C:\MED-PC\CoasterChase\ tree existing.
    If this passes, ANY failure of the production file is a logic bug,
    not a toolchain problem.

  DEPLOY:
    1. Back up the stock C:\MED-PC\BACKPROC.PAS  (e.g. copy to BACKPROC.PAS.stock).
    2. Replace the BODIES of BackProc1 and BackProc2 in the stock file
       with the two procedures below.  KEEP the stock file's unit header,
       any `uses` clause, and any procedures past BackProc2 -- only the
       bodies of 1 and 2 change.
    3. Open SmokeTest.mpc in MED-PC and run
          Translation | Batch Translate!
       MED-PC auto-recompiles BACKPROC.PAS when the source changed
       (DOC-301 p.215).  No separate compiler command.
    4. Load Box 1 with SmokeTest, press START, watch the screen show
       fields update.  Pass criteria are in smoke_test/SmokeTest.mpc.

  REVERT after smoke test passes:
    Restore the stock BACKPROC.PAS (or drop in medpc/BACKPROC.PAS for the
    real integration) and re-run Batch Translate!.

  Procedure contract (DOC-301 p.211, verbatim):
       Procedure BackProcN(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
  and the LAST executed line MUST be  BackRequest[Box][N] := False;
  =========================================================================== }


Procedure BackProc1(MPCGlobal: MPCGlobalPtr; Box: Byte); Export;
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
      BackRequest[Box][1] := False;                   { MANDATORY (proc 1) }
   End;
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
