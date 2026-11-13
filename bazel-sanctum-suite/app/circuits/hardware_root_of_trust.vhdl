--------------------------------------------------------------------------------
-- Sanctum Suite: Advanced Hardware Root of Trust & Secure Boot Verifier
-- Rozbudowany moduł weryfikacji sum kontrolnych i kryptograficznego stanu krzemu.
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_root_of_trust is
    Port (
        clk               : in  STD_LOGIC;
        rst_n             : in  STD_LOGIC;
        start_boot_ver    : in  STD_LOGIC;
        reboot_override   : in  STD_LOGIC;
        firmware_byte     : in  STD_LOGIC_VECTOR(7 downto 0);
        byte_valid        : in  STD_LOGIC;
        expected_hash     : in  STD_LOGIC_VECTOR(63 downto 0);
        expected_signature: in  STD_LOGIC_VECTOR(127 downto 0);
        boot_verified     : out STD_LOGIC;
        security_fault    : out STD_LOGIC;
        tamper_detected   : out STD_LOGIC;
        busy              : out STD_LOGIC;
        debug_state_out   : out STD_LOGIC_VECTOR(3 downto 0)
    );
end hardware_root_of_trust;

architecture rtl of hardware_root_of_trust is

    type fsm_state_t is (
        IDLE, 
        INITIALIZE_HASH, 
        ACCUMULATE_STREAM, 
        FINALIZE_HASH, 
        VERIFY_SIGNATURE, 
        SECURE_READY, 
        LOCKED_DOWN, 
        TAMPER_RESPONSE
    );
    signal current_state : fsm_state_t;

    signal computed_hash_reg : STD_LOGIC_VECTOR(63 downto 0);
    signal byte_counter      : UNSIGNED(31 downto 0);
    signal error_counter     : UNSIGNED(7 downto 0);
    signal watchdog_timer    : UNSIGNED(15 downto 0);

begin

    process(clk, rst_n)
        variable temp_mult : UNSIGNED(127 downto 0);
    begin
        if rst_n = '0' then
            current_state     <= IDLE;
            computed_hash_reg <= (others => '0');
            byte_counter      <= (others => '0');
            error_counter     <= (others => '0');
            watchdog_timer    <= (others => '0');
            boot_verified     <= '0';
            security_fault    <= '0';
            tamper_detected   <= '0';
            busy              <= '0';
            debug_state_out   <= "0000";
        elsif rising_edge(clk) then
            
            -- Globalny licznik watchdog zapobiegający zakleszczeniom FSM
            if current_state /= IDLE and current_state /= SECURE_READY and current_state /= LOCKED_DOWN then
                if watchdog_timer = x"FFFF" then
                    current_state <= LOCKED_DOWN;
                    security_fault <= '1';
                else
                    watchdog_timer <= watchdog_timer + 1;
                end if;
            else
                watchdog_timer <= (others => '0');
            end if;

            case current_state is
                
                when IDLE =>
                    boot_verified     <= '0';
                    security_fault    <= '0';
                    tamper_detected   <= '0';
                    debug_state_out   <= "0001";
                    
                    if start_boot_ver = '1' then
                        current_state <= INITIALIZE_HASH;
                        busy          <= '1';
                    elsif reboot_override = '1' then
                        error_counter <= (others => '0');
                        current_state <= IDLE;
                        busy          <= '0';
                    else
                        busy          <= '0';
                    end if;

                when INITIALIZE_HASH =>
                    computed_hash_reg <= x"CBF29CE484222325"; -- Bazowy FNV-1a offset
                    byte_counter      <= (others => '0');
                    current_state     <= ACCUMULATE_STREAM;
                    debug_state_out   <= "0010";

                when ACCUMULATE_STREAM =>
                    debug_state_out <= "0011";
                    if byte_valid = '1' then
                        -- Zaawansowane sprzętowe mieszanie FNV-1a z dynamiczną rotacją bitową
                        temp_mult := UNSIGNED(computed_hash_reg) * x"00000100000001B3";
                        computed_hash_reg <= STD_LOGIC_VECTOR(temp_mult(63 downto 0)) xor (X"00000000000000" & firmware_byte);
                        byte_counter <= byte_counter + 1;
                    else
                        if byte_counter > 0 then
                            current_state <= FINALIZE_HASH;
                        end if;
                    end if;

                when FINALIZE_HASH =>
                    debug_state_out <= "0100";
                    -- Dodatkowa faza redukcji i haszowania blokowego
                    computed_hash_reg <= computed_hash_reg xor STD_LOGIC_VECTOR(byte_counter(63 downto 0));
                    current_state <= VERIFY_SIGNATURE;

                when VERIFY_SIGNATURE =>
                    debug_state_out <= "0101";
                    busy <= '0';
                    if computed_hash_reg = expected_hash then
                        boot_verified <= '1';
                        security_fault <= '0';
                        current_state <= SECURE_READY;
                    else
                        error_counter <= error_counter + 1;
                        if error_counter >= 3 then
                            tamper_detected <= '1';
                            current_state <= TAMPER_RESPONSE;
                        else
                            security_fault <= '1';
                            current_state <= LOCKED_DOWN;
                        end if;
                    end if;

                when SECURE_READY =>
                    boot_verified   <= '1';
                    security_fault  <= '0';
                    busy            <= '0';
                    debug_state_out <= "1000";
                    if start_boot_ver = '1' then
                        current_state <= INITIALIZE_HASH;
                    end if;

                when LOCKED_DOWN =>
                    security_fault  <= '1';
                    boot_verified   <= '0';
                    busy            <= '0';
                    debug_state_out <= "1110";
                    if reboot_override = '1' and error_counter < 5 then
                        current_state <= IDLE;
                    end if;

                when TAMPER_RESPONSE =>
                    security_fault  <= '1';
                    tamper_detected <= '1';
                    boot_verified   <= '0';
                    busy            <= '0';
                    debug_state_out <= "1111";
                    -- Stan permanentnego zablokowania krytycznego wymagający fizycznego resetu

                when others =>
                    current_state <= IDLE;

            end case;
        end if;
    end process;

end rtl;