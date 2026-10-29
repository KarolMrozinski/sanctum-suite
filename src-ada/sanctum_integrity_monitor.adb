package body Sanctum.Audit.Integrity is

   procedure Register_Component (Monitor : in out Integrity_Monitor_Context;
                                 ID      : in Natural;
                                 Hash    : in Natural) is
   begin
      if Monitor.Count < Monitor.Max_Components then
         Monitor.Count := Monitor.Count + 1;
         Monitor.Components (Monitor.Count) := (Component_ID   => ID,
                                                Expected_Hash  => Hash,
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
               Monitor.Components (I).Is_Compromised := True;
               Monitor.Global_OK := False;
            end if;
         end if;
      end loop;
   end Verify_Component;

   function Get_Global_Status (Monitor : in Integrity_Monitor_Context) return System_Health_Status is
   begin
      if Monitor.Global_OK then
         return Optimal;
      else
         return Critical_Breach;
      end if;
   end Get_Global_Status;

end Sanctum.Audit.Integrity;