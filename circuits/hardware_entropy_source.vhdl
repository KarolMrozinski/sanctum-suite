--------------------------------------------------------------------------------
-- Sanctum Suite: Hardware True Random Number Generator (TRNG) & Entropy Source
-- Generowanie stanów losowych opartych na jitterze oscylatora pierścieniowego.
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_entropy_source is
    Port (
        clk             : in  STD_LOGIC;
        rst_n           : in  STD_LOGIC;
        enable_entropy  : in  STD_LOGIC;
        raw_jitter_in   : in  STD_LOGIC; -- Wejście z fizycznego oscylatora pierścieniowego
        entropy_out     : out STD_LOGIC_VECTOR(31 downto 0);
        entropy_ready   : out STD_LOGIC
    );
end hardware_entropy_source;

architecture rtl of hardware_entropy_source is

    signal lfsr_register : STD_LOGIC_VECTOR(31 downto 0);
    signal bit_counter   : UNSIGNED(5 downto 0);

begin

    process(clk, rst_n)
        variable feedback : STD_LOGIC;
    begin
        if rst_n = '0' then
            lfsr_register <= x"DEADBEEF";
            bit_counter   <= (others => '0');
            entropy_out   <= (others => '0');
            entropy_ready <= '0';
        elsif rising_edge(clk) then
            if enable_entropy = '1' then
                -- Sprzętowe mieszanie jittera fizycznego z LFSR
                feedback := lfsr_register[31] xor lfsr_register[21] xor lfsr_register[2] xor raw_jitter_in;
                lfsr_register <= lfsr_register[30 downto 0] & feedback;
                
                bit_counter <= bit_counter + 1;
                if bit_counter = 31 then
                    entropy_out   <= lfsr_register;
                    entropy_ready <= '1';
                else
                    entropy_ready <= '0';
                end if;
            else
                entropy_ready <= '0';
            end if;
        end if;
    end process;

end rtl;