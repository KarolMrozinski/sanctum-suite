with Ada.Containers.Indefinite_Hashed_Maps;
with Ada.Strings.Unbounded;
with Ada.Calendar;

package Sanctum.Crypto.Vault is

   use Ada.Strings.Unbounded;
   use Ada.Calendar;

   type Vault_State_Enum is (Locked, Unlocked, Compromised_Lockdown, Maintenance_Mode, Rotating_Keys);
   
   -- Wyjątki bezpieczeństwa krytycznego
   Vault_Access_Denied   : exception;
   Vault_Buffer_Overflow : exception;
   Vault_Tamper_Error    : exception;
   Vault_Locked_Error    : exception;
   Vault_Crypto_Failure  : exception;

   type Secret_Record is record
      Cipher_Data   : Unbounded_String;
      Metadata_Tag  : Unbounded_String;
      Created_At    : Time;
      Last_Accessed : Time;
      Access_Hits   : Natural := 0;
      Key_Version   : Positive := 1;
   end record;

   package Secret_Maps is new Ada.Containers.Indefinite_Hashed_Maps
     (Key_Type        => String,
      Element_Type    => Secret_Record,
      Hash            => Ada.Strings.Hash,
      Equivalent_Keys => "=");

   -- Obiekt chroniony (Protected Object) gwarantujący bezpieczną współbieżność w systemach wielordzeniowych
   protected type Secure_Vault_Manager (Max_Capacity : Positive) is
      procedure Initialize_Vault (Master_Token : in String; Salt : in String);
      procedure Unlock_Vault (Master_Token : in String);
      procedure Lock_Vault;
      procedure Rotate_Master_Key (New_Token : in String);
      
      procedure Store_Secret (Key : in String; Data : in String; Tag : in String);
      function Retrieve_Secret (Key : in String) return String;
      
      function Get_State return Vault_State_Enum;
      function Get_Audit_Tally return Natural;
      function Verify_Integrity_Checksum return Boolean;
   private
      State           : Vault_State_Enum := Locked;
      Master_Hash     : Natural := 0;
      Salt_Value      : Unbounded_String;
      Storage         : Secret_Maps.Map;
      Access_Count    : Natural := 0;
      Failed_Attempts : Natural := 0;
      Key_Generation  : Positive := 1;
   end Secure_Vault_Manager;

end Sanctum.Crypto.Vault;