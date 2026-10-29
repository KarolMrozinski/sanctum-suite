package body Sanctum.Audit.Integrity is

   procedure Register_Component (Monitor : in out Integrity_Monitor_Context;
                                 ID      : in Natural;
                                 Hash    : in Natural) is
   begin
      if Monitor.Count < Monitor.Max_Components then
         Monitor.Count := Monitor.Count + 1;
         Monitor.Components (Monitor.Count) := (Component_ID   => ID,
                                                Expected_Hash  => Hash,
                                                Fail_Count     => 0,
                                                Is_Compromised => False);
      end if;
   end Register_Component;

   procedure Verify_Component (Monitor : in out Integrity_Monitor_Context;
                               ID      : in Natural;
                               Current : in Natural) is
   begin
      for I in 1 .. Monitor.Count loop
         if Monitor.Components (I).Component_ID = ID then
            if Monitor.Components (I).Expected_Hash /= Current then
               Monitor.Components (I).Fail_Count := Monitor.Components (I).Fail_Count + 1;
               Monitor.Components (I).Is_Compromised := True;
               Monitor.Breach_Tally := Monitor.Breach_Tally + 1;
               Monitor.Global_OK := False;
            end if;
         end if;
      end loop;
   end Verify_Component;

   function Get_Global_Status (Monitor : in Integrity_Monitor_Context) return System_Health_Status is
   begin
      if Monitor.Global_OK then
         return Optimal;
      elsif Monitor.Breach_Tally < 3 then
         return Warning;
      elsif Monitor.Breach_Tally < 6 then
         return Critical_Breach;
      else
         return System_Halt;
      end if;
   end Get_Global_Status;

   procedure Reset_Component_State (Monitor : in out Integrity_Monitor_Context; ID : in Natural) is
   begin
      for I in 1 .. Monitor.Count loop
         if Monitor.Components (I).Component_ID = ID then
            Monitor.Components (I).Is_Compromised := False;
            Monitor.Components (I).Fail_Count := 0;
         end if;
      end loop;
   end Reset_Component_State;

end Sanctum.Audit.Integrity;