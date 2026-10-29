package body Sanct.Network.Guard is

   function Inspect_Packet (Packet : in Packet_Metadata) return Action_Policy is
      Is_Local_Source : Boolean;
   begin
      -- Sprawdzenie czy adres źródłowy jest prywatny lub loopback w trybie Air-Gapped
      Is_Local_Source := (Packet.Source_IP (1) = 10) or 
                         (Packet.Source_IP (1) = 192 and then Packet.Source_IP (2) = 168) or
                         (Packet.Source_IP (1) = 127);

      if Packet.Is_Strict_Air and then not Is_Local_Source then
         return Drop;
      end if;

      if Packet.Payload_Length > 65535 then
         return Quarantined;
      end if;

      return Allow;
   end Inspect_Packet;

end Sanct.Network.Guard;