--------------------------------------------------------------------------------
-- Sanctum Suite: Hardware Root of Trust & Secure Boot Verifier
-- Odpowiada za weryfikację sum kontrolnych BIOS/Firmware na poziomie FPGA/ASIC.
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_root_of_trust is
    Port (
        clk             : in  STD_LOGIC;
        rst_n           : in  STD_LOGIC;
        start_boot_ver  : in  STD_LOGIC;
        firmware_byte   : in  STD_LOGIC_VECTOR(7 downto 0);
        byte_valid      : in  STD_LOGIC;
        expected_hash   : in  STD_LOGIC_VECTOR(63 downto 0);
        boot_verified   : out STD_LOGIC;
        security_fault  : out STD_LOGIC;
        busy            : out STD_LOGIC
    );
end hardware_root_of_trust;

architecture rtl of hardware_root_of_trust is

    type fsm_state_t is (IDLE, COMPUTING, VERIFYING, LOCKED_DOWN, SECURE_READY);
    signal current_state : fsm_state_t;

    signal computed_hash_reg : STD_LOGIC_VECTOR(63 downto 0);
    signal byte_counter      : UNSIGNED(31 downto 0);

begin

    process(clk, rst_n)
        variable hash_acc : STD_LOGIC_VECTOR(63 downto 0);
    begin
        if rst_n = '0' then
            current_state       <= IDLE;
            computed_hash_reg   <= (others => '0');
            byte_counter        <= (others => '0');
            boot_verified       <= '0';
            security_fault      <= '0';
            busy                <= '0';
        elsif rising_edge(clk) then
            case current_state is
                
                when IDLE =>
                    boot_verified     <= '0';
                    security_fault    <= '0';
                    if start_boot_ver = '1' then
                        current_state     <= COMPUTING;
                        computed_hash_reg <= x"CBF29CE484222325"; -- FNV-1a basis
                        byte_counter      <= (others => '0');
                        busy              <= '1';
                    else
                        busy              <= '0';
                    end if;

                when COMPUTING =>
                    if byte_valid = '1' then
                        -- Sprzętowa akumulacja hasha FNV-1a
                        computed_hash_reg <= STD_LOGIC_VECTOR(
                            UNSIGNED(computed_hash_reg) xor X"00000000000000" & UNSIGNED(firmware_byte)
                        ) * x"00000100000001B3";
                        byte_counter <= byte_counter + 1;
                    else
                        -- Koniec strumienia bajtów firmware
                        if byte_counter > 0 then
                            current_state <= VERIFYING;
                        end if;
                    end if;

                when VERIFYING =>
                    busy <= '0';
                    if computed_hash_reg = expected_hash then
                        boot_verified <= '1';
                        current_state <= SECURE_READY;
                    else
                        security_fault <= '1';
                        current_state <= LOCKED_DOWN;
                    end if;

                when LOCKED_DOWN =>
                    -- Stan trwały zablokowania w przypadku naruszenia sumy kontrolnej
                    security_fault <= '1';
                    boot_verified  <= '0';
                    busy           <= '0';

                when SECURE_READY =>
                    boot_verified <= '1';
                    busy          <= '0';
                    if rst_n = '0' then
                        current_state <= IDLE;
                    end if;

                when others =>
                    current_state <= IDLE;

            end case;
        end if;
    end process;

end rtl;