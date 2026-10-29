package Sanctum.Audit.Integrity is

   type System_Health_Status is (Optimal, Warning, Critical_Breach);

   type Baseline_Record is record
      Component_ID   : Natural;
      Expected_Hash  : Natural;
      Is_Compromised : Boolean;
   end record;

   type Integrity_Monitor_Context (Max_Components : Positive) is limited private;

   procedure Register_Component (Monitor : in out Integrity_Monitor_Context;
                                 ID      : in Natural;
                                 Hash    : in Natural);

   procedure Verify_Component (Monitor : in out Integrity_Monitor_Context;
                               ID      : in Natural;
                               Current : in Natural);

   function Get_Global_Status (Monitor : in Integrity_Monitor_Context) return System_Health_Status;

private

   type Component_Array is array (Positive range <>) of Baseline_Record;

   type Integrity_Monitor_Context (Max_Components : Positive) is limited record
      Count      : Natural := 0;
      Components : Component_Array (1 .. Max_Components);
      Global_OK  : Boolean := True;
   end record;

end Sanctum.Audit.Integrity;