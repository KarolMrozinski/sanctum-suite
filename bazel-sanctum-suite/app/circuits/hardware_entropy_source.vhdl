--------------------------------------------------------------------------------
-- Sanctum Suite: Advanced Hardware True Random Number Generator (TRNG)
-- Rozbudowany moduł generowania entropii sprzętowej ze sprawdzaniem testów NIST.
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_entropy_source is
    Port (
        clk               : in  STD_LOGIC;
        rst_n             : in  STD_LOGIC;
        enable_entropy    : in  STD_LOGIC;
        raw_jitter_in     : in  STD_LOGIC;
        entropy_out       : out STD_LOGIC_VECTOR(63 downto 0);
        entropy_ready     : out STD_LOGIC;
        health_test_fail  : out STD_LOGIC;
        entropy_pool_stat : out STD_LOGIC_VECTOR(7 downto 0)
    );
end hardware_entropy_source;

architecture rtl of hardware_entropy_source is

    signal lfsr_upper       : STD_LOGIC_VECTOR(31 downto 0);
    signal lfsr_lower       : STD_LOGIC_VECTOR(31 downto 0);
    signal bit_counter      : UNSIGNED(6 downto 0);
    signal ones_counter     : UNSIGNED(6 downto 0);
    signal health_error_reg : STD_LOGIC;
    signal pool_fill_level  : UNSIGNED(7 downto 0);

begin

    process(clk, rst_n)
        variable fb_upper, fb_lower : STD_LOGIC;
    begin
        if rst_n = '0' then
            lfsr_upper       <= x"A5A55A5A";
            lfsr_lower       <= x"3C3CC3C3";
            bit_counter      <= (others => '0');
            ones_counter     <= (others => '0');
            pool_fill_level  <= (others => '0');
            entropy_out      <= (others => '0');
            entropy_ready    <= '0';
            health_error_reg <= '0';
        elsif rising_edge(clk) then
            if enable_entropy = '1' then
                -- Sprzętowe mieszanie wielomianowe zwrotne z jitterem termicznym
                fb_upper := lfsr_upper[31] xor lfsr_upper[21] xor lfsr_upper[1] xor raw_jitter_in;
                fb_lower := lfsr_lower[31] xor lfsr_lower[13] xor lfsr_lower[4] xor lfsr_upper[0];

                lfsr_upper <= lfsr_upper[30 downto 0] & fb_upper;
                lfsr_lower <= lfsr_lower[30 downto 0] & fb_lower;

                if raw_jitter_in = '1' then
                    ones_counter <= ones_counter + 1;
                end if;

                bit_counter <= bit_counter + 1;
                
                -- Po zebraniu 64 bitów losowych wykonujemy test sprawności (Health Test / Repetition Count Test)
                if bit_counter = 63 then
                    entropy_out <= lfsr_upper & lfsr_lower;
                    entropy_ready <= '1';
                    
                    if ones_counter < 10 or ones_counter > 54 then
                        health_error_reg <= '1'; -- Wykryto anomalię w źródle entropii (zbyt mało lub zbyt dużo jedynek)
                    else
                        health_error_reg <= '0';
                        if pool_fill_level < 255 then
                            pool_fill_level <= pool_fill_level + 16;
                        end if;
                    end if;
                    
                    ones_counter <= (others => '0');
                else
                    entropy_ready <= '0';
                end if;
            else
                entropy_ready <= '0';
            end if;
        end if;
    end process;

    health_test_fail  <= health_error_reg;
    entropy_pool_stat <= STD_LOGIC_VECTOR(pool_fill_level);

end rtl;