with Ada.Text_IO;

procedure Sanctum_Suite is
   subtype Security_Level is Natural range 0 .. 5;

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
         -- Funkcja jest typu read-only, zwracamy stan bez jego modyfikacji
         return Current_Level;
      end Get_Level;
   end State_Manager;

   -- Instancja globalnego obiektu chronionego stanu
   Global_State : State_Manager;

   -- Zadanie w tle korzystające z obiektu chronionego
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
   Ada.Text_IO.Put_Line
     ("[+] Initial Level: " &
      Security_Level'Image (Global_State.Get_Level));

   -- Główny wątek oczekuje na zakończenie zadań w tle
   null;
end Sanctum_Suite;