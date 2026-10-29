with Ada.Containers.Indefinite_Hashed_Maps;
with Ada.Strings.Unbounded;

package Sanctum.Crypto.Vault is

   use Ada.Strings.Unbounded;

   type Vault_State_Enum is (Locked, Unlocked, Compromised_Lockdown);
   
   type Secure_Vault_Context (Max_Capacity : Natural) is limited private;

   -- Wyjątki bezpieczeństwa
   Vault_Access_Denied : exception;
   Vault_Buffer_Overflow : exception;
   Vault_Tamper_Error : exception;

   procedure Initialize_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String);
   
   procedure Unlock_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String);
   
   procedure Lock_Vault (Vault : in out Secure_Vault_Context);

   procedure Store_Secret (Vault : in out Secure_Vault_Context; 
                           Key   : in String; 
                           Data  : in String);

   function Retrieve_Secret (Vault : in Secure_Vault_Context; 
                             Key   : in String) return String;

   function Get_State (Vault : in Secure_Vault_Context) return Vault_State_Enum;

private

   package String_Maps is new Ada.Containers.Indefinite_Hashed_Maps
     (Key_Type        => String,
      Element_Type    => Unbounded_String,
      Hash            => Ada.Strings.Hash,
      Equivalent_Keys => "=");

   type Secure_Vault_Context (Max_Capacity : Natural) is limited record
      State         : Vault_State_Enum := Locked;
      Master_Hash   : Natural := 0;
      Storage       : String_Maps.Map;
      Access_Count  : Natural := 0;
   end record;

end Sanctum.Crypto.Vault;