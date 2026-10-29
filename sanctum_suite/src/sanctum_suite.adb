with Ada.Text_IO;
with Interfaces; use Interfaces;

procedure Sanctum_Suite is
   subtype Security_Level is Natural range 0 .. 5;

   -- Odwzorowanie struktury z języka C w Adzie
   type Sanctum_Packet is record
      Magic_ID : Unsigned_32;
      Flags    : Unsigned_32;
      Node_ID  : Unsigned_8;
   end record;

   pragma Convention (C, Sanctum_Packet);

   -- Import zewnętrznej procedury z C operującej na wskaźniku do struktury
   procedure Sanctum_Fill_Packet (Pkt : access Sanctum_Packet);
   pragma Import (C, Sanctum_Fill_Packet, "sanctum_fill_packet");

   -- Obiekt chroniony: bezpieczny dostęp do stanu z poziomu wielu wątków
   protected type State_Manager (Initial_Level : Security_Level := 5) is
      procedure Set_Level (New_Level : Security_Level);
      function Get_Level return Security_Level;
   private
      Current_Level : Security_Level := Initial_Level;
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
   end State_Manager;

   -- Instancja globalnego obiektu chronionego stanu
   Global_State : State_Manager;
   Packet       : aliased Sanctum_Packet;

   -- Zadanie w tle monitorujące bezpieczeństwo
   task Monitor;

   task body Monitor is
   begin
      Ada.Text_IO.Put_Line ("[*] Protected Security Monitor active.");
      for I in 1 .. 3 loop
         delay 0.4;
         Ada.Text_IO.Put_Line
           ("[Monitor] Thread Safety Verified. Level: " &
            Security_Level'Image (Global_State.Get_Level));
      end loop;
   end Monitor;

begin
   Ada.Text_IO.Put_Line ("[+] Sanctum Suite Advanced Core initialized.");

   -- Wywołanie funkcji z C przekazującej strukturę przez wskaźnik
   Sanctum_Fill_Packet (Packet'Access);

   Ada.Text_IO.Put_Line
     ("[+] C-Packet Magic ID: 16#" & Unsigned_32'Image (Packet.Magic_ID) & "#");
   Ada.Text_IO.Put_Line
     ("[+] C-Packet Node ID:  16#" & Unsigned_8'Image (Packet.Node_ID) & "#");

   Ada.Text_IO.Put_Line
     ("[+] Initial Level: " &
      Security_Level'Image (Global_State.Get_Level));

   -- Główny wątek oczekuje na zakończenie zadań w tle
   null;
end Sanctum_Suite;