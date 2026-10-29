--------------------------------------------------------------------------------
-- Sanctum Suite: Hardware Packet Firewall & MAC/IP Interceptor
-- Sprzętowa inspekcja ramek w czasie rzeczywistym (wire-speed drop/allow).
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_packet_firewall is
    Port (
        clk             : in  STD_LOGIC;
        rst_n           : in  STD_LOGIC;
        frame_data      : in  STD_LOGIC_VECTOR(7 downto 0);
        frame_valid     : in  STD_LOGIC;
        strict_air_gap  : in  STD_LOGIC;
        drop_packet     : out STD_LOGIC;
        allow_packet    : out STD_LOGIC;
        anomaly_flag    : out STD_LOGIC
    );
end hardware_packet_firewall;

architecture rtl of hardware_packet_firewall is

    signal byte_index   : UNSIGNED(15 downto 0);
    signal is_external  : STD_LOGIC;

begin

    process(clk, rst_n)
    begin
        if rst_n = '0' then
            byte_index   <= (others => '0');
            is_external  <= '0';
            drop_packet  <= '0';
            allow_packet <= '0';
            anomaly_flag <= '0';
        elsif rising_edge(clk) then
            if frame_valid = '1' then
                byte_index <= byte_index + 1;

                -- Przykładowa inspekcja nagłówka IP (bajty 12-15 to Source IP)
                if byte_index = 12 then
                    -- Jeśli pierwszy oktet IP to np. adres publiczny w trybie strict air-gap
                    if strict_air_gap = '1' and frame_data /= x"0A" and frame_data /= x"C0" then
                        is_external <= '1';
                    else
                        is_external <= '0';
                    end if;
                end if;

                if byte_index > 1500 then -- Przekroczenie standardowego MTU
                    anomaly_flag <= '1';
                end if;

            else
                -- Koniec ramki – podjęcie decyzji
                if byte_index > 0 then
                    if is_external = '1' and strict_air_gap = '1' then
                        drop_packet  <= '1';
                        allow_packet <= '0';
                        anomaly_flag <= '1';
                    else
                        drop_packet  <= '0';
                        allow_packet <= '1';
                    end if;
                end;
                byte_index <= (others => '0');
            end if;
        end if;
    end process;

end rtl;