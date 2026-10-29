with Ada.Containers.Indefinite_Hashed_Maps;
with Ada.Strings.Unbounded;
with Ada.Calendar;

package Sanctum.Crypto.Vault is

   use Ada.Strings.Unbounded;
   use Ada.Calendar;

   type Vault_State_Enum is (Locked, Unlocked, Compromised_Lockdown, Maintenance_Mode);
   
   type Secure_Vault_Context (Max_Capacity : Natural) is limited private;

   Vault_Access_Denied : exception;
   Vault_Buffer_Overflow : exception;
   Vault_Tamper_Error : exception;
   Vault_Locked_Error : exception;

   procedure Initialize_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String; Salt : in String);
   
   procedure Unlock_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String);
   
   procedure Lock_Vault (Vault : in out Secure_Vault_Context);

   procedure Store_Secret (Vault : in out Secure_Vault_Context; 
                           Key   : in String; 
                           Data  : in String;
                           Tag   : in String);

   function Retrieve_Secret (Vault : in Secure_Vault_Context; 
                             Key   : in String) return String;

   function Get_State (Vault : in Secure_Vault_Context) return Vault_State_Enum;
   
   function Get_Audit_Trail_Count (Vault : in Secure_Vault_Context) return Natural;

private

   type Secret_Record is record
      Cipher_Data : Unbounded_String;
      Metadata_Tag: Unbounded_String;
      Created_At  : Time;
      Access_Hits : Natural := 0;
   end record;

   package Secret_Maps is new Ada.Containers.Indefinite_Hashed_Maps
     (Key_Type        => String,
      Element_Type    => Secret_Record,
      Hash            => Ada.Strings.Hash,
      Equivalent_Keys => "=");

   type Secure_Vault_Context (Max_Capacity : Natural) is limited record
      State         : Vault_State_Enum := Locked;
      Master_Hash   : Natural := 0;
      Salt_Value    : Unbounded_String;
      Storage       : Secret_Maps.Map;
      Access_Count  : Natural := 0;
      Failed_Attempts : Natural := 0;
   end record;

end Sanctum.Crypto.Vault;