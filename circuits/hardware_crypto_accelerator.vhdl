--------------------------------------------------------------------------------
-- Sanctum Suite: High-Throughput Hardware Crypto & Packet Accelerator (FPGA)
-- Zapewnia równoległe, potokowe przetwarzanie i haszowanie strumieniowe w czasie rzeczywistym.
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity hardware_crypto_accelerator is
    Port (
        clk               : in  STD_LOGIC;
        rst_n             : in  STD_LOGIC;
        stream_data_in    : in  STD_LOGIC_VECTOR(31 downto 0);
        data_valid_in     : in  STD_LOGIC;
        encryption_mode   : in  STD_LOGIC; -- '0' = FNV-1a Hash, '1' = XOR Cipher Stream
        secret_key_mask   : in  STD_LOGIC_VECTOR(31 downto 0);
        stream_data_out   : out STD_LOGIC_VECTOR(31 downto 0);
        data_valid_out    : out STD_LOGIC;
        accelerator_busy  : out STD_LOGIC;
        anomaly_detected  : out STD_LOGIC
    );
end hardware_crypto_accelerator;

architecture rtl of hardware_crypto_accelerator is

    -- Rejestry potoku (Pipeline Registers) dla maksymalnej wydajności taktowania
    signal stage1_data    : STD_LOGIC_VECTOR(31 downto 0);
    signal stage1_valid   : STD_LOGIC;
    signal stage2_hash    : STD_LOGIC_VECTOR(31 downto 0);
    signal stage2_valid   : STD_LOGIC;
    
    -- Wewnętrzne stany akceleratora
    signal processing_active : STD_LOGIC;
    signal error_counter     : UNSIGNED(15 downto 0);

begin

    process(clk, rst_n)
        variable temp_calc : UNSIGNED(63 downto 0);
    begin
        if rst_n = '0' then
            stage1_data       <= (others => '0');
            stage1_valid      <= '0';
            stage2_hash       <= x"811C9DC5"; -- Standardowy offset FNV-32
            stage2_valid      <= '0';
            stream_data_out   <= (others => '0');
            data_valid_out    <= '0';
            accelerator_busy  <= '0';
            anomaly_detected  <= '0';
            processing_active <= '0';
            error_counter     <= (others => '0');
        elsif rising_edge(clk) then
            
            -- Etap 1: Pobieranie danych i wstępne maskowanie kluczem
            if data_valid_in = '1' then
                processing_active <= '1';
                accelerator_busy  <= '1';
                
                if encryption_mode = '1' then
                    -- Tryb szyfrowania strumieniowego XOR z maską
                    stage1_data  <= stream_data_in xor secret_key_mask;
                else
                    -- Tryb surowego strumienia do akceleracji hashowania
                    stage1_data  <= stream_data_in;
                end if;
                stage1_valid <= '1';
            else
                stage1_valid <= '0';
                accelerator_busy <= '0';
            end if;

            -- Etap 2: Potokowe obliczanie hasha FNV-32 lub transformacji
            if stage1_valid = '1' then
                if encryption_mode = '0' then
                    -- Sprzętowa multiplikacja FNV w jednym cyklu zegara
                    temp_calc := UNSIGNED(stage2_hash xor stage1_data) * x"01000193";
                    stage2_hash <= STD_LOGIC_VECTOR(temp_calc(31 downto 0));
                else
                    stage2_hash <= stage1_data;
                end if;
                stage2_valid <= '1';
            else
                stage2_valid <= '0';
            end if;

            -- Etap 3: Wyprowadzenie zbuforowanego wyniku na wyjście akceleratora
            if stage2_valid = '1' then
                stream_data_out <= stage2_hash;
                data_valid_out  <= '1';
                
                -- Detekcja anomalii (np. wykrycie wzorca ataku / overflow w strumieniu)
                if stage2_hash = x"DEADBEEF" or stage2_hash = x"00000000" then
                    anomaly_detected <= '1';
                    error_counter    <= error_counter + 1;
                else
                    anomaly_detected <= '0';
                end if;
            else
                data_valid_out <= '0';
            end if;

        end if;
    end process;

end rtl;