package body Sanctum.Network.Guard is

   function Validate_Port_Range (Port : in Natural) return Boolean is
   begin
      return Port > 0 and Port <= 65535;
   end Validate_Port_Range;

   function Verify_IP_Format (IP : in IP_Octet_Array) return Boolean is
   begin
      for I in IP'Range loop
         if IP (I) > 255 then
            return False;
         end if;
      end loop;
      return True;
   end Verify_IP_Format;

   function Inspect_Packet (Packet : in Packet_Metadata; Stats : in out Firewall_Statistics) return Action_Policy is
      Is_Local_Source : Boolean;
      Result          : Action_Policy;
   begin
      Stats.Total_Inspected := Stats.Total_Inspected + 1;

      if not Verify_IP_Format (Packet.Source_IP) or not Verify_IP_Format (Packet.Dest_IP) then
         Stats.Total_Dropped := Stats.Total_Dropped + 1;
         Stats.Anomaly_Count := Stats.Anomaly_Count + 1;
         return Drop;
      end if;

      if not Validate_Port_Range (Packet.Source_Port) or not Validate_Port_Range (Packet.Dest_Port) then
         Stats.Total_Dropped := Stats.Total_Dropped + 1;
         return Drop;
      end if;

      -- Sprawdzenie przestrzeni adresowej w trybie Air-Gapped
      Is_Local_Source := (Packet.Source_IP (1) = 10) or 
                         (Packet.Source_IP (1) = 192 and then Packet.Source_IP (2) = 168) or
                         (Packet.Source_IP (1) = 172 and then Packet.Source_IP (2) >= 16 and then Packet.Source_IP (2) <= 31) or
                         (Packet.Source_IP (1) = 127);

      if Packet.Is_Strict_Air and then not Is_Local_Source then
         Stats.Total_Dropped := Stats.Total_Dropped + 1;
         Stats.Anomaly_Count := Stats.Anomaly_Count + 1;
         return Drop;
      end if;

      if Packet.Payload_Length > 1500 and then not Packet.Is_Encrypted then
         Result := Deep_Inspect_Required;
      elsif Packet.Payload_Length > 65535 then
         Stats.Total_Dropped := Stats.Total_Dropped + 1;
         Result := Quarantined;
      else
         Stats.Total_Allowed := Stats.Total_Allowed + 1;
         Result := Allow;
      end if;

      return Result;
   end Inspect_Packet;

end Sanctum.Network.Guard;