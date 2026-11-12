pragma circom 2.1.6;

include "../node_modules/circomlib/circuits/poseidon.circom";

/*
 * Sanctum Suite: Config Integrity Verifier Circuit
 * Umożliwia udowodnienie znajomości tajnego klucza konfiguracyjnego 
 * bez jego ujawniania w otwartej sieci / środowisku odizolowanym.
 */
template ConfigVerifier() {
    // Sygnały wejściowe (prywatne)
    signal input secretConfigKey;
    
    // Sygnały wejściowe (publiczne)
    signal input expectedHash;

    // Sygnał wyjściowy
    signal output isValid;

    // Komponent wyliczający hash Poseidon
    component hasher = Poseidon(1);
    hasher.inputs[0] <== secretConfigKey;

    // Sprawdzenie poprawności hasha
    hasher.out === expectedHash;
    
    isValid <== 1;
}

component main {public [expectedHash]} = ConfigVerifier();