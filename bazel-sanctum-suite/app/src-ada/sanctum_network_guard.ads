package Sanctum.Network.Guard is

   type Action_Policy is (Allow, Drop, Quarantined, Deep_Inspect_Required, Rate_Limited);
   
   type IP_Octet_Array is array (1 .. 4) of Natural;

   type Packet_Metadata is record
      Source_IP      : IP_Octet_Array;
      Dest_IP        : IP_Octet_Array;
      Source_Port    : Natural;
      Dest_Port      : Natural;
      Payload_Length : Natural;
      Protocol_ID    : Natural;
      Is_Strict_Air  : Boolean;
      Is_Encrypted   : Boolean;
      Header_Checksum: Natural;
   end record;

   type Firewall_Statistics is record
      Total_Inspected : Natural;
      Total_Dropped   : Natural;
      Total_Allowed   : Natural;
      Anomaly_Count   : Natural;
   end record;

   function Inspect_Packet (Packet : in Packet_Metadata; Stats : in out Firewall_Statistics) return Action_Policy;
   function Validate_Port_Range (Port : in Natural) return Boolean;
   function Verify_IP_Format (IP : in IP_Octet_Array) return Boolean;

end Sanctum.Network.Guard;