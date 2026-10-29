package Sanctum.Audit.Integrity is

   type System_Health_Status is (Optimal, Warning, Critical_Breach, System_Halt, Self_Healing_Active);

   type Baseline_Record is record
      Component_ID    : Natural;
      Expected_Hash   : Natural;
      Fallback_Hash   : Natural;
      Fail_Count      : Natural;
      Is_Compromised  : Boolean;
      Auto_Recoverable: Boolean;
   end record;

   type Integrity_Monitor_Context (Max_Components : Positive) is limited private;

   procedure Register_Component (Monitor : in out Integrity_Monitor_Context;
                                 ID              : in Natural;
                                 Expected_Hash   : in Natural;
                                 Fallback_Hash   : in Natural;
                                 Recoverable     : in Boolean);

   procedure Verify_Component (Monitor : in out Integrity_Monitor_Context;
                               ID      : in Natural;
                               Current : in Natural);

   function Get_Global_Status (Monitor : in Integrity_Monitor_Context) return System_Health_Status;
   
   procedure Execute_Self_Healing (Monitor : in out Integrity_Monitor_Context; ID : in Natural);
   procedure Reset_Monitor_State (Monitor : in out Integrity_Monitor_Context);

private

   type Component_Array is array (Positive range <>) of Baseline_Record;

   type Integrity_Monitor_Context (Max_Components : Positive) is limited record
      Count        : Natural := 0;
      Components   : Component_Array (1 .. Max_Components);
      Global_OK    : Boolean := True;
      Breach_Tally : Natural := 0;
      Healing_Mode : Boolean := False;
   end record;

end Sanctum.Audit.Integrity;