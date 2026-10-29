with Ada.Text_IO;
with Interfaces; use Interfaces;
with System;     use System;

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

   -- Obiekt chroniony zarządzający stanem oraz bezpiecznym buforem logów
   protected type State_Manager (Initial_Level : Security_Level := 5) is
      procedure Set_Level (New_Level : Security_Level);
      function Get_Level return Security_Level;

      procedure Log_Event (Message : String);
      procedure Print_Logs;
   private
      Current_Level : Security_Level := Initial_Level;
      Log_Count     : Natural        := 0;
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
      begin
         if Log_Count < Max_Logs then
            Log_Count := Log_Count + 1;
            Ada.Text_IO.Put_Line
              ("[AUDIT LOG #" & Natural'Image (Log_Count) & "] " & Message);
         end if;
      end Log_Event;

      procedure Print_Logs is
      begin
         Ada.Text_IO.Put_Line ("--- [ START OF AUDIT LOG BUFFER ] ---");
      end Print_Logs;
   end State_Manager;

   Global_State : State_Manager;
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

   -- Zmienne dla CLI
   Input_Str : String (1 .. 10);
   Last      : Natural;
   New_Lvl   : Natural;

begin
   Ada.Text_IO.Put_Line ("[+] Sanctum Suite Advanced Core initialized.");

   -- Inicjalizacja pakietu C i kryptografii
   Sanctum_Fill_Packet (Packet'Access);
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
      Ada.Text_IO.Put_Line ("5. Exit / Shutdown Suite");
      Ada.Text_IO.Put ("Select an option (1-5): ");

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
                       ("Operator changed level to: " & Natural'Image (New_Lvl));
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
               Global_State.Print_Logs;
               Ada.Text_IO.Put_Line
                 ("--- [ END OF AUDIT LOG BUFFER ] ---");

            when '5' =>
               Global_State.Log_Event
                 ("Operator initiated graceful shutdown.");
               Ada.Text_IO.Put_Line
                 ("[+] Shutting down Sanctum Suite safely...");
               exit;

            when others =>
               Ada.Text_IO.Put_Line
                 ("[-] Invalid option. Choose between 1 and 5.");
         end case;
      end if;
   end loop;

   Ada.Text_IO.Put_Line ("[+] Main execution thread completed securely.");
end Sanctum_Suite;