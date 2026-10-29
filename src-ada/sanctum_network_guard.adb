package body Sanctum.Network.Guard is

   function Validate_Port_Range (Port : in Natural) return Boolean is
   begin
      return Port > 0 and Port <= 65535;
   end Validate_Port_Range;

   function Inspect_Packet (Packet : in Packet_Metadata) return Action_Policy is
      Is_Local_Source : Boolean;
   begin
      if not Validate_Port_Range (Packet.Source_Port) or not Validate_Port_Range (Packet.Dest_Port) then
         return Drop;
      end if;

      -- Weryfikacja przestrzeni prywatnej w trybie Air-Gapped
      Is_Local_Source := (Packet.Source_IP (1) = 10) or 
                         (Packet.Source_IP (1) = 192 and then Packet.Source_IP (2) = 168) or
                         (Packet.Source_IP (1) = 172 and then Packet.Source_IP (2) >= 16 and then Packet.Source_IP (2) <= 31) or
                         (Packet.Source_IP (1) = 127);

      if Packet.Is_Strict_Air and then not Is_Local_Source then
         return Drop;
      end if;

      if Packet.Payload_Length > 1500 and then not Packet.Is_Encrypted then
         return Deep_Inspect_Required;
      end if;

      if Packet.Payload_Length > 65535 then
         return Quarantined;
      end if;

      return Allow;
   end Inspect_Packet;

end Sanctum.Network.Guard;