package body Sanctum.Crypto.Vault is

   procedure Initialize_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String) is
      Accumulator : Natural := 0;
   begin
      for I in Master_Token'Range loop
         Accumulator := Accumulator + Character.Pos (Master_Token (I));
      end loop;
      Vault.Master_Hash := Accumulator;
      Vault.State := Locked;
   end Initialize_Vault;

   procedure Unlock_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String) is
      Accumulator : Natural := 0;
   begin
      for I in Master_Token'Range loop
         Accumulator := Accumulator + Character.Pos (Master_Token (I));
      end loop;

      if Accumulator = Vault.Master_Hash then
         Vault.State := Unlocked;
         Vault.Access_Count := 0;
      else
         Vault.State := Compromised_Lockdown;
         raise Vault_Access_Denied;
      end if;
   end Unlock_Vault;

   procedure Lock_Vault (Vault : in out Secure_Vault_Context) is
   begin
      Vault.State := Locked;
      Vault.Storage.Clear;
   end Lock_Vault;

   procedure Store_Secret (Vault : in out Secure_Vault_Context; 
                           Key   : in String; 
                           Data  : in String) is
   begin
      if Vault.State /= Unlocked then
         raise Vault_Access_Denied;
      end if;

      if Natural (Vault.Storage.Length) >= Vault.Max_Capacity then
         raise Vault_Buffer_Overflow;
      end if;

      Vault.Storage.Include (Key, To_Unbounded_String (Data));
   end Store_Secret;

   function Retrieve_Secret (Vault : in Secure_Vault_Context; 
                             Key   : in String) return String is
   begin
      if Vault.State /= Unlocked then
         raise Vault_Access_Denied;
      end if;

      if Vault.Storage.Contains (Key) then
         return To_String (Vault.Storage.Element (Key));
      else
         raise Vault_Buffer_Overflow;
      end if;
   end Retrieve_Secret;

   function Get_State (Vault : in Secure_Vault_Context) return Vault_State_Enum is
   begin
      return Vault.State;
   end Get_State;

end Sanctum.Crypto.Vault;