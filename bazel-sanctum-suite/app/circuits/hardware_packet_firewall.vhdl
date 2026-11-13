--------------------------------------------------------------------------------
-- Sanctum Suite: Advanced Hardware Packet Firewall & MAC/IP Interceptor
-- Rozbudowany, wysokowydajny filtr ramek sieciowych w czasie rzeczywistym.
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_packet_firewall is
    Port (
        clk               : in  STD_LOGIC;
        rst_n             : in  STD_LOGIC;
        frame_data        : in  STD_LOGIC_VECTOR(7 downto 0);
        frame_valid       : in  STD_LOGIC;
        strict_air_gap    : in  STD_LOGIC;
        whitelist_mode    : in  STD_LOGIC;
        drop_packet       : out STD_LOGIC;
        allow_packet      : out STD_LOGIC;
        anomaly_flag      : out STD_LOGIC;
        rate_limit_exceed : out STD_LOGIC;
        packet_stats_out  : out STD_LOGIC_VECTOR(31 downto 0)
    );
end hardware_packet_firewall;

architecture rtl of hardware_packet_firewall is

    type firewall_state_t is (PARSE_IDLE, PARSE_ETH_HEADER, PARSE_IP_HEADER, INSPECT_PAYLOAD, DROP_STATE, ALLOW_STATE);
    signal current_state : firewall_state_t;

    signal byte_index      : UNSIGNED(15 downto 0);
    signal packet_counter  : UNSIGNED(31 downto 0);
    signal drop_counter    : UNSIGNED(15 downto 0);
    signal is_external_ip  : STD_LOGIC;
    signal is_malformed    : STD_LOGIC;

begin

    process(clk, rst_n)
    begin
        if rst_n = '0' then
            current_state     <= PARSE_IDLE;
            byte_index        <= (others => '0');
            packet_counter    <= (others => '0');
            drop_counter      <= (others => '0');
            is_external_ip    <= '0';
            is_malformed      <= '0';
            drop_packet       <= '0';
            allow_packet      <= '0';
            anomaly_flag      <= '0';
            rate_limit_exceed <= '0';
        elsif rising_edge(clk) then
            case current_state is

                when PARSE_IDLE =>
                    drop_packet  <= '0';
                    allow_packet <= '0';
                    anomaly_flag <= '0';
                    if frame_valid = '1' then
                        byte_index <= to_unsigned(1, 16);
                        current_state <= PARSE_ETH_HEADER;
                    end if;

                when PARSE_ETH_HEADER =>
                    if frame_valid = '1' then
                        byte_index <= byte_index + 1;
                        if byte_index = 13 then -- Koniec nagłówka Ethernet, przejście do IP
                            current_state <= PARSE_IP_HEADER;
                        end if;
                    else
                        current_state <= PARSE_IDLE;
                    end if;

                when PARSE_IP_HEADER =>
                    if frame_valid = '1' then
                        byte_index <= byte_index + 1;
                        
                        -- Sprawdzenie pierwszego oktetu źródłowego IP (bajty 26-29 w ramce z Ethernetem)
                        if byte_index = 26 then
                            if strict_air_gap = '1' and frame_data /= x"0A" and frame_data /= x"C0" and frame_data /= x"7F" then
                                is_external_ip <= '1';
                            else
                                is_external_ip <= '0';
                            end if;
                        end if;

                        if byte_index >= 1518 then -- Przekroczenie limitu jumbo frame / standardowego MTU
                            is_malformed <= '1';
                        end if;

                        -- Po zakończeniu nagłówka IP przechodzimy do inspekcji ładunku
                        if byte_index = 34 then
                            current_state <= INSPECT_PAYLOAD;
                        end if;
                    else
                        current_state <= PARSE_IDLE;
                    end if;

                when INSPECT_PAYLOAD =>
                    if frame_valid = '1' then
                        byte_index <= byte_index + 1;
                    else
                        -- Koniec ramki – ocena polityk bezpieczeństwa
                        packet_counter <= packet_counter + 1;
                        if (is_external_ip = '1' and strict_air_gap = '1') or is_malformed = '1' then
                            current_state <= DROP_STATE;
                        else
                            current_state <= ALLOW_STATE;
                        end if;
                    end if;

                when DROP_STATE =>
                    drop_packet  <= '1';
                    allow_packet <= '0';
                    anomaly_flag <= '1';
                    drop_counter <= drop_counter + 1;
                    if drop_counter > 100 then
                        rate_limit_exceed <= '1';
                    end if;
                    current_state <= PARSE_IDLE;

                when ALLOW_STATE =>
                    drop_packet  <= '0';
                    allow_packet <= '1';
                    anomaly_flag <= '0';
                    current_state <= PARSE_IDLE;

                when others =>
                    current_state <= PARSE_IDLE;

            end case;
        end if;
    end process;

    packet_stats_out <= STD_LOGIC_VECTOR(packet_counter);

end rtl;