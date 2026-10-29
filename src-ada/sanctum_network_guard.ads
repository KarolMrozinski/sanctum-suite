package Sanct.Network.Guard is

   type Action_Policy is (Allow, Drop, Quarantined);
   
   type IP_Octet_Array is array (1 .. 4) of Natural;

   type Packet_Metadata is record
      Source_IP      : IP_Octet_Array;
      Dest_IP        : IP_Octet_Array;
      Source_Port    : Natural;
      Dest_Port      : Natural;
      Payload_Length : Natural;
      Is_Strict_Air  : Boolean;
   end record;

   function Inspect_Packet (Packet : in Packet_Metadata) return Action_Policy;

end Sanct.Network.Guard;