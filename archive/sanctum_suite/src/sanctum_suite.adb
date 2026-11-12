with Ada.Text_IO;
with Interfaces;   use Interfaces;
with System;       use System;
with GNAT.Sockets; use GNAT.Sockets;

procedure Sanctum_Suite is
   subtype Security_Level is Natural range 0 .. 5;

   Max_Logs : constant := 20;

   type Sanctum_Packet is record
      Magic_ID : Unsigned_32;
      Flags    : Unsigned_32;
      Node_ID  : Unsigned_8;
   end record;

   pragma Convention (C, Sanctum_Packet);

   -- Import procedur z języka C
   procedure Sanctum_Fill_Packet (Pkt : access Sanctum_Packet);
   pragma Import (C, Sanctum_Fill_Packet, "sanctum_fill_packet");

   function Sanctum_Compute_Hash
     (Data   : System.Address;
      Length : Unsigned_32) return Unsigned_32;
   pragma Import (C, Sanctum_Compute_Hash, "sanctum_compute_hash");

   procedure Sanctum_Encrypt_Buffer
     (Data    : System.Address;
      Length  : Unsigned_32;
      Key     : System.Address;
      Key_Len : Unsigned_32);
   pragma Import (C, Sanctum_Encrypt_Buffer, "sanctum_encrypt_buffer");

   -- Zmienne konfiguracyjne wczytywane z pliku
   Config_Sec_Level : Security_Level := 5;
   Config_Port      : Port_Type      := 5555;
   Config_Node_ID   : Unsigned_8     := 16#42#;
   Encryption_Key   : aliased constant String := "SANCTUM_SECURE_256_BIT_KEY_ALPHA";

   -- Forward specyfikacje procedur pomocniczych
   procedure Save_Logs_To_Disk;
   procedure Transmit_Network_Telemetry;
   procedure Load_Configuration;

   -- Obiekt chroniony zarządzający stanem oraz bezpiecznym buforem logów
   protected type State_Manager (Initial_Level : Security_Level := 5) is
      procedure Set_Level (New_Level : Security_Level);
      function Get_Level return Security_Level;

      procedure Log_Event (Message : String);
      procedure Get_Logs (Logs : out String; Length : out Natural);
   private
      Current_Level : Security_Level     := Initial_Level;
      Log_Buffer    : String (1 .. 2000) := (others => ' ');
      Cursor        : Natural            := 0;
   end State_Manager;

   protected body State_Manager is
      procedure Set_Level (New_Level : Security_Level) is
      begin
         Current_Level := New_Level;
      end Set_Level;

      function Get_Level return Security_Level is
      begin
         return Current_Level;
      end Get_Level;

      procedure Log_Event (Message : String) is
         Formatted : constant String := "[AUDIT] " & Message & ASCII.LF;
      begin
         if Cursor + Formatted'Length <= Log_Buffer'Length then
            Log_Buffer (Cursor + 1 .. Cursor + Formatted'Length) := Formatted;
            Cursor := Cursor + Formatted'Length;
         end if;
      end Log_Event;

      procedure Get_Logs (Logs : out String; Length : out Natural) is
      begin
         Length := Natural'Min (Cursor, Logs'Length);
         Logs (1 .. Length) := Log_Buffer (1 .. Length);
      end Get_Logs;
   end State_Manager;

   Global_State : State_Manager (Config_Sec_Level);
   Packet       : aliased Sanctum_Packet;
   Hash_Result  : Unsigned_32;

   -- Zadanie w tle monitorujące bezpieczeństwo
   task Monitor;

   task body Monitor is
   begin
      Global_State.Log_Event ("Protected Security Monitor task started.");
      for I in 1 .. 2 loop
         delay 0.5;
         Global_State.Log_Event
           ("Thread Safety Verified. Current Level: " &
            Security_Level'Image (Global_State.Get_Level));
      end loop;
   end Monitor;

   -- Procedura wczytująca konfigurację z pliku zewnętrznego
   procedure Load_Configuration is
      File : Ada.Text_IO.File_Type;
      Line : String (1 .. 80);
      Last : Natural;
   begin
      Ada.Text_IO.Open
        (File => File,
         Mode => Ada.Text_IO.In_File,
         Name => "sanctum_config.cfg");

      while not Ada.Text_IO.End_Of_File (File) loop
         Ada.Text_IO.Get_Line (File, Line, Last);
         if Last >= 16 and then Line (1 .. 15) = "SECURITY_LEVEL=" then
            Config_Sec_Level := Security_Level'Value
              (Line (16 .. Last));
         elsif Last >= 13 and then Line (1 .. 12) = "SOCKET_PORT=" then
            Config_Port := Port_Type'Value
              (Line (13 .. Last));
         elsif Last >= 15 and then Line (1 .. 14) = "NODE_IDENTIFIER=" then
            Config_Node_ID := Unsigned_8'Value
              (Line (15 .. Last));
         end if;
      end loop;
      Ada.Text_IO.Close (File);
      Ada.Text_IO.Put_Line
        ("[+] Configuration successfully loaded from 'sanctum_config.cfg'.");
   exception
      when others =>
         Ada.Text_IO.Put_Line
           ("[-] Notice: Using default configuration values (config not found).");
   end Load_Configuration;

   -- Procedura zapisująca logi na dysk
   procedure Save_Logs_To_Disk is
      File   : Ada.Text_IO.File_Type;
      Logs   : String (1 .. 2000);
      Length : Natural;
   begin
      Global_State.Get_Logs (Logs, Length);
      Ada.Text_IO.Create (File, Ada.Text_IO.Out_File, "sanctum_audit.log");
      Ada.Text_IO.Put (File, Logs (1 .. Length));
      Ada.Text_IO.Close (File);
      Ada.Text_IO.Put_Line
        ("[+] Audit logs successfully persisted to 'sanctum_audit.log'.");
   exception
      when others =>
         Ada.Text_IO.Put_Line
           ("[-] Error: Failed to write audit logs to disk.");
   end Save_Logs_To_Disk;

   -- Procedura obsługująca transmisję sieciową telemetrii przez GNAT.Sockets
   procedure Transmit_Network_Telemetry is
      Sock    : Socket_Type;
      Addr    : Sock_Addr_Type;
      Data    : constant String := "SANCTUM_SUITE_TELEMETRY_BEACON";
      Channel : Stream_Access;
   begin
      Initialize;
      Create_Socket (Sock, Family_Inet, Socket_Datagram);
      Addr.Addr := Inet_Addr ("127.0.0.1");
      Addr.Port := Config_Port;

      Channel := Stream (Sock, Addr);
      String'Output (Channel, Data);
      Close_Socket (Sock);

      Global_State.Log_Event
        ("Telemetry broadcasted successfully over network socket.");
      Ada.Text_IO.Put_Line
        ("[+] Telemetry beacon sent to 127.0.0.1:" &
         Port_Type'Image (Config_Port) & " (UDP).");
   exception
      when others =>
         Global_State.Log_Event ("Network telemetry transmission failed.");
         Ada.Text_IO.Put_Line
           ("[-] Network Error: Unable to transmit telemetry packet.");
         begin
            Close_Socket (Sock);
         exception
            when others => null;
         end;
   end Transmit_Network_Telemetry;

   -- Zmienne dla CLI
   Input_Str : String (1 .. 10);
   Last      : Natural;
   New_Lvl   : Natural;

begin
   Ada.Text_IO.Put_Line ("[+] Sanctum Suite Advanced Core initialized.");

   -- Wczytanie zewnętrznej konfiguracji przed inicjalizacją modułów
   Load_Configuration;

   -- Inicjalizacja pakietu C i kryptografii
   Sanctum_Fill_Packet (Packet'Access);
   Packet.Node_ID := Config_Node_ID;
   Global_State.Log_Event
     ("C-Module hardware packet successfully parsed.");

   Hash_Result := Sanctum_Compute_Hash
     (Data   => Packet'Address,
      Length => Unsigned_32'Val (Sanctum_Packet'Size / 8));
   Global_State.Log_Event
     ("Cryptographic integrity hash computed via C.");

   -- Główna pętla interfejsu CLI dla operatora
   loop
      Ada.Text_IO.New_Line;
      Ada.Text_IO.Put_Line ("=== SANCTUM SUITE OPERATOR CLI ===");
      Ada.Text_IO.Put_Line ("1. Display System Status");
      Ada.Text_IO.Put_Line ("2. Change Security Level (0-5)");
      Ada.Text_IO.Put_Line ("3. View Hardware Packet & Hash");
      Ada.Text_IO.Put_Line ("4. Print Audit Log Buffer");
      Ada.Text_IO.Put_Line ("5. Save Audit Logs to Disk (Persistent)");
      Ada.Text_IO.Put_Line ("6. Transmit Network Telemetry (Sockets)");
      Ada.Text_IO.Put_Line ("7. Encrypt / Decrypt Packet via C (AES-256)");
      Ada.Text_IO.Put_Line ("8. Exit / Shutdown Suite");
      Ada.Text_IO.Put ("Select an option (1-8): ");

      Ada.Text_IO.Get_Line (Input_Str, Last);

      if Last >= 1 then
         case Input_Str (1) is
            when '1' =>
               Ada.Text_IO.Put_Line
                 ("[*] Current Security Level: " &
                  Security_Level'Image (Global_State.Get_Level));

            when '2' =>
               Ada.Text_IO.Put ("Enter new security level (0-5): ");
               Ada.Text_IO.Get_Line (Input_Str, Last);
               begin
                  New_Lvl := Natural'Value (Input_Str (1 .. Last));
                  if New_Lvl <= 5 then
                     Global_State.Set_Level (Security_Level (New_Lvl));
                     Global_State.Log_Event
                       ("Operator changed level to: " &
                        Natural'Image (New_Lvl));
                     Ada.Text_IO.Put_Line
                       ("[+] Security level updated successfully.");
                  else
                     Ada.Text_IO.Put_Line
                       ("[-] Error: Level must be between 0 and 5.");
                  end if;
               exception
                  when others =>
                     Ada.Text_IO.Put_Line
                       ("[-] Error: Invalid numeric input.");
               end;

            when '3' =>
               Ada.Text_IO.Put_Line
                 ("[+] Packet Magic ID: 16#" &
                  Unsigned_32'Image (Packet.Magic_ID) & "#");
               Ada.Text_IO.Put_Line
                 ("[+] Packet Node ID:  16#" &
                  Unsigned_8'Image (Packet.Node_ID) & "#");
               Ada.Text_IO.Put_Line
                 ("[+] Integrity Hash:  16#" &
                  Unsigned_32'Image (Hash_Result) & "#");

            when '4' =>
               declare
                  Logs   : String (1 .. 2000);
                  Length : Natural;
               begin
                  Global_State.Get_Logs (Logs, Length);
                  Ada.Text_IO.Put_Line
                    ("--- [ START OF AUDIT LOG BUFFER ] ---");
                  Ada.Text_IO.Put (Logs (1 .. Length));
                  Ada.Text_IO.Put_Line
                    ("--- [ END OF AUDIT LOG BUFFER ] ---");
               end;

            when '5' =>
               Save_Logs_To_Disk;

            when '6' =>
               Transmit_Network_Telemetry;

            when '7' =>
               Sanctum_Encrypt_Buffer
                 (Data    => Packet'Address,
                  Length  => Unsigned_32'Val (Sanctum_Packet'Size / 8),
                  Key     => Encryption_Key'Address,
                  Key_Len => Encryption_Key'Length);
               Global_State.Log_Event
                 ("Packet payload encrypted/decrypted via C AES-256 cipher.");
               Ada.Text_IO.Put_Line
                 ("[+] Packet successfully ciphered/deciphered in memory.");

            when '8' =>
               Global_State.Log_Event
                 ("Operator initiated graceful shutdown.");
               Save_Logs_To_Disk;
               Ada.Text_IO.Put_Line
                 ("[+] Shutting down Sanctum Suite safely...");
               exit;

            when others =>
               Ada.Text_IO.Put_Line
                 ("[-] Invalid option. Choose between 1 and 8.");
         end case;
      end if;
   end loop;

   Ada.Text_IO.Put_Line ("[+] Main execution thread completed securely.");
end Sanctum_Suite;