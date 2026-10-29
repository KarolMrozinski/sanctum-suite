with Ada.Text_IO;

procedure Sanctum_Suite is
   -- Przykładowy ściśle kontrolowany podtyp (bezpieczeństwo zakresu)
   subtype Security_Level is Natural range 0 .. 5;
   
   Current_Level : Security_Level := 5;
begin
   Ada.Text_IO.Put_Line("[+] Sanctum Suite Core initialized successfully.");
   Ada.Text_IO.Put_Line("[+] Active Security Level: " & Security_Level'Image(Current_Level));
   
   -- Tutaj wdrożymy kolejne mechanizmy współbieżności (Tasking)
end Sanctum_Suite;