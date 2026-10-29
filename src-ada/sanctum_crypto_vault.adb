package body Sanctum.Crypto.Vault is

   procedure Initialize_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String; Salt : in String) is
      Accumulator : Natural := 0;
   begin
      for I in Master_Token'Range loop
         Accumulator := Accumulator + Character.Pos (Master_Token (I));
      end loop;
      for J in Salt'Range loop
         Accumulator := Accumulator xor Character.Pos (Salt (J));
      end loop;

      Vault.Master_Hash := Accumulator;
      Vault.Salt_Value := To_Unbounded_String (Salt);
      Vault.State := Locked;
      Vault.Failed_Attempts := 0;
   end Initialize_Vault;

   procedure Unlock_Vault (Vault : in out Secure_Vault_Context; Master_Token : in String) is
      Accumulator : Natural := 0;
   begin
      if Vault.State = Compromised_Lockdown then
         raise Vault_Locked_Error;
      end if;

      for I in Master_Token'Range loop
         Accumulator := Accumulator + Character.Pos (Master_Token (I));
      end loop;
      
      -- Dodanie wymieszania z solą
      for K in 1 .. Length (Vault.Salt_Value) loop
         Accumulator := Accumulator xor Character.Pos (Element (Vault.Salt_Value, K));
      end loop;

      if Accumulator = Vault.Master_Hash then
         Vault.State := Unlocked;
         Vault.Access_Count := 0;
         Vault.Failed_Attempts := 0;
      else
         Vault.Failed_Attempts := Vault.Failed_Attempts + 1;
         if Vault.Failed_Attempts >= 3 then
            Vault.State := Compromised_Lockdown;
         end if;
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
                           Data  : in String;
                           Tag   : in String) is
   begin
      if Vault.State /= Unlocked then
         raise Vault_Access_Denied;
      end if;

      if Natural (Vault.Storage.Length) >= Vault.Max_Capacity then
         raise Vault_Buffer_Overflow;
      end if;

      declare
         New_Record : Secret_Record := (
            Cipher_Data  => To_Unbounded_String (Data),
            Metadata_Tag => To_Unbounded_String (Tag),
            Created_At   => Clock,
            Access_Hits  => 0
         );
      begin
         Vault.Storage.Include (Key, New_Record);
      end;
   end Store_Secret;

   function Retrieve_Secret (Vault : in Secure_Vault_Context; 
                             Key   : in String) return String is
   begin
      if Vault.State /= Unlocked then
         raise Vault_Access_Denied;
      end if;

      if Vault.Storage.Contains (Key) then
         return To_String (Vault.Storage.Element (Key).Cipher_Data);
      else
         raise Vault_Buffer_Overflow;
      end if;
   end Retrieve_Secret;

   function Get_State (Vault : in Secure_Vault_Context) return Vault_State_Enum is
   begin
      return Vault.State;
   end Get_State;

   function Get_Audit_Trail_Count (Vault : in Secure_Vault_Context) return Natural is
   begin
      return Vault.Access_Count;
   end Get_Audit_Trail_Count;

end Sanctum.Crypto.Vault;