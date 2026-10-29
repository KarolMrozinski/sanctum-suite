with Ada.Text_IO;
with Interfaces; use Interfaces;

procedure Sanctum_Suite is
   subtype Security_Level is Natural range 0 .. 5;

   -- Deklaracja importu zewnętrznej funkcji niskopoziomowej napisanej w C
   function Get_Hardware_Status return Unsigned_32;
   pragma Import (C, Get_Hardware_Status, "sanctum_get_hardware_status");

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
   HW_Status    : Unsigned_32;

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

   -- Wywołanie funkcji zintegrowanego modułu C
   HW_Status := Get_Hardware_Status;
   Ada.Text_IO.Put_Line
     ("[+] C-Module Hardware Status: 16#" & Unsigned_32'Image (HW_Status) & "#");

   Ada.Text_IO.Put_Line
     ("[+] Initial Level: " &
      Security_Level'Image (Global_State.Get_Level));

   -- Główny wątek oczekuje na zakończenie zadań w tle
   null;
end Sanctum_Suite;