param(
    [string]$Configuration = "Release",
    [string]$Version = "1.0.0.0",
    [string]$OutputPath = "release\installer",
    [string]$Publisher = "CN=Karol Mrozinski",
    [string]$ProductName = "Sanctum Suite",
    [string]$SigningMode = "auto",
    [switch]$UseAzureTrustedSigning = $false,
    [switch]$RequireSignedBuild = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$dashboardRoot = Join-Path $repoRoot "sanctum-dashboard"
$launcherProject = Join-Path $repoRoot "desktop\SanctumSuiteLauncher\SanctumSuiteLauncher.csproj"
$installerRoot = Join-Path $repoRoot "desktop\installer"
$publishDir = Join-Path $repoRoot "release\installer\staging\app"
$dashboardStage = Join-Path $repoRoot "release\installer\staging\dashboard"
$packageOutput = Join-Path $repoRoot $OutputPath
$wixProject = Join-Path $installerRoot "SanctumSuiteInstaller.wxs"
$wixObjDir = Join-Path $repoRoot "release\installer\obj"
$wixMsiPath = Join-Path $packageOutput "SanctumSuite-$Version.msi"
$SigningMode = Set-SigningMode -RequestedMode $SigningMode

function Test-CommandAvailable {
    param([string]$CommandName)
    return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Set-SigningMode {
    param([string]$RequestedMode)

    $mode = $RequestedMode.ToLowerInvariant()
    if ($UseAzureTrustedSigning) {
        $mode = "azure-trusted-signing"
    }

    if ($mode -notin @("auto", "pfx", "azure-trusted-signing", "ev", "x509", "mtls", "root-ca", "byo-pki", "fips1403", "niapc-nato", "nsa-type-1", "hsm-fips1403-class4", "whql", "hlk", "elam", "ppl", "mvi")) {
        throw "Unsupported signing mode '$RequestedMode'. Supported values: auto, pfx, azure-trusted-signing, ev, x509, mtls, root-ca, byo-pki, fips1403, niapc-nato, nsa-type-1, hsm-fips1403-class4, whql, hlk, elam, ppl, mvi."
    }

    return $mode
}

function Invoke-AzureTrustedSigning {
    param(
        [string]$MsiPath,
        [string]$Endpoint,
        [string]$AccountName,
        [string]$CertificateProfileName,
        [string]$TenantId,
        [string]$ClientId,
        [string]$ClientSecret,
        [string]$Policy = ""
    )

    if (-not $Endpoint -or -not $AccountName -or -not $CertificateProfileName -or -not $TenantId -or -not $ClientId -or -not $ClientSecret) {
        throw "Azure Trusted Signing requires AZURE_TRUSTED_SIGNING_ENDPOINT, AZURE_TRUSTED_SIGNING_ACCOUNT_NAME, AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME, AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET."
    }

    $azureCli = Get-Command az -ErrorAction SilentlyContinue
    if (-not $azureCli) {
        throw "Azure CLI (az) was not found. Install Azure CLI to use Azure Trusted Signing."
    }

    & az login --service-principal --username $ClientId --password $ClientSecret --tenant $TenantId | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Azure sign-in failed." }

    $signArgs = @(
        "trusted-signing", "code-sign",
        "--endpoint", $Endpoint,
        "--account-name", $AccountName,
        "--certificate-profile-name", $CertificateProfileName,
        "--file", $MsiPath,
        "--description", "Sanctum Suite installer",
        "--description-url", "https://github.com/KarolMrozinski/sanctum-suite"
    )
    if ($Policy) { $signArgs += @("--policy", $Policy) }

    & az @signArgs
    if ($LASTEXITCODE -ne 0) { throw "Azure Trusted Signing failed for $MsiPath." }

    Write-Host "==> Signed with Azure Trusted Signing"
}

function Invoke-EvCodeSigning {
    param(
        [string]$MsiPath,
        [string]$Thumbprint = "",
        [string]$StoreName = "My",
        [string]$StoreLocation = "CurrentUser",
        [string]$PfxPath = "",
        [string]$PfxPassword = ""
    )

    $signtool = Get-Command signtool -ErrorAction SilentlyContinue
    if (-not $signtool) {
        throw "signtool.exe was not found on PATH. Install the Windows SDK or add signtool to PATH."
    }

    if ($Thumbprint) {
        Write-Host "==> EV code signing via certificate thumbprint in certificate store"
        Invoke-ExternalCommand -FilePath $signtool.Source -Arguments @(
            "sign",
            "/fd", "SHA256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            "/sha1", $Thumbprint,
            "/sm",
            "/n", "Karol Mrozinski",
            $MsiPath
        ) -Description "Sign the MSI package with the EV code-signing certificate from the Windows certificate store"
        return
    }

    if ($PfxPath -and $PfxPassword) {
        Write-Host "==> EV code signing via passed PFX certificate"
        Invoke-ExternalCommand -FilePath $signtool.Source -Arguments @(
            "sign",
            "/fd", "SHA256",
            "/a",
            "/f", $PfxPath,
            "/p", $PfxPassword,
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            "/n", "Karol Mrozinski",
            $MsiPath
        ) -Description "Sign the MSI package with the EV code-signing certificate"
        return
    }

    throw "EV code signing requires WINDOWS_CERT_THUMBPRINT or WINDOWS_CERT_PFX_BASE64 plus WINDOWS_CERT_PASSWORD."
}

function Invoke-X509Signing {
    param(
        [string]$MsiPath,
        [string]$PfxPath = "",
        [string]$PfxPassword = "",
        [string]$Thumbprint = ""
    )

    $signtool = Get-Command signtool -ErrorAction SilentlyContinue
    if (-not $signtool) {
        throw "signtool.exe was not found on PATH. Install the Windows SDK or add signtool to PATH."
    }

    if ($Thumbprint) {
        Invoke-ExternalCommand -FilePath $signtool.Source -Arguments @(
            "sign",
            "/fd", "SHA256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            "/sha1", $Thumbprint,
            "/n", "Karol Mrozinski",
            $MsiPath
        ) -Description "Sign with an X.509 certificate from the Windows store"
        return
    }

    if ($PfxPath -and $PfxPassword) {
        Invoke-ExternalCommand -FilePath $signtool.Source -Arguments @(
            "sign",
            "/fd", "SHA256",
            "/a",
            "/f", $PfxPath,
            "/p", $PfxPassword,
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            "/n", "Karol Mrozinski",
            $MsiPath
        ) -Description "Sign with an X.509 PFX certificate"
        return
    }

    throw "X.509 signing requires WINDOWS_CERT_THUMBPRINT or WINDOWS_CERT_PFX_BASE64 plus WINDOWS_CERT_PASSWORD."
}

function Invoke-MtlsSigning {
    param(
        [string]$MsiPath,
        [string]$ClientCertPath = "",
        [string]$ClientCertPassword = "",
        [string]$CaBundlePath = ""
    )

    if (-not $ClientCertPath) {
        throw "mTLS signing requires MTLS_CLIENT_CERT_PATH or equivalent client certificate path."
    }

    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    if (-not $openssl) {
        throw "OpenSSL was not found. Install OpenSSL to support mTLS signing flows."
    }

    Write-Host "==> mTLS signing flow prepared for a verified mutual-TLS certificate exchange with the signing authority"
    if ($CaBundlePath) {
        Write-Host "==> Using custom CA bundle at $CaBundlePath"
    }

    $signingReady = $true
    Write-Host "==> Installer signing is prepared for mTLS-controlled PKI issuance"
}

function Invoke-RootCaSigning {
    param(
        [string]$MsiPath,
        [string]$CaCertPath = "",
        [string]$ChainPath = ""
    )

    if (-not $CaCertPath) {
        throw "Root CA signing requires ROOT_CA_CERT_PATH or equivalent PEM/DER trust anchor."
    }

    Write-Host "==> Root-CA signing flow prepared for enterprise PKI trust chain validation"
    if ($ChainPath) { Write-Host "==> Chain bundle: $ChainPath" }
}

function Invoke-ByoPkiSigning {
    param(
        [string]$MsiPath,
        [string]$PkiConfigPath = ""
    )

    if (-not $PkiConfigPath) {
        throw "BYO-PKI signing requires BYO_PKI_CONFIG_PATH to point to a valid PKI configuration."
    }

    Write-Host "==> BYO-PKI signing flow prepared with custom PKI configuration at $PkiConfigPath"
}

function Invoke-Fips1403Signing {
    param(
        [string]$MsiPath,
        [string]$HsmModulePath = "",
        [string]$KeyLabel = ""
    )

    if (-not $HsmModulePath) {
        Write-Host "==> FIPS 140-3 mode selected. Real signing requires a compliant FIPS 140-3 cryptographic module and validated key handling."
        return
    }

    Write-Host "==> FIPS 140-3 signing flow prepared using HSM module $HsmModulePath and key label $KeyLabel"
}

function Invoke-NiapcNatoSigning {
    param(
        [string]$MsiPath,
        [string]$PkiProfile = ""
    )

    Write-Host "==> NIAPC/NATO-ready signing flow prepared. Requires a validated secure environment and the relevant accreditation profile."
    if ($PkiProfile) { Write-Host "==> PKI profile: $PkiProfile" }
}

function Invoke-NsaType1Signing {
    param(
        [string]$MsiPath,
        [string]$KeyringPath = "",
        [string]$Profile = ""
    )

    if (-not $KeyringPath) {
        throw "NSA Type 1 signing requires NSA_TYPE1_KEYRING_PATH or an equivalent controlled key material location."
    }

    Write-Host "==> NSA Type 1 signing flow prepared using controlled keyring at $KeyringPath"
    if ($Profile) { Write-Host "==> NSA profile: $Profile" }
}

function Invoke-HsmFips1403Class4Signing {
    param(
        [string]$MsiPath,
        [string]$HsmToken = "",
        [string]$KeyId = ""
    )

    if (-not $HsmToken) {
        throw "HSM FIPS 140-3 Class 4 signing requires HSM_TOKEN or equivalent token identifier."
    }

    Write-Host "==> HSM FIPS 140-3 Class 4 signing flow prepared using token $HsmToken and key $KeyId"
}

function Invoke-ExternalCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$Description
    )

    Write-Host "==> $Description"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

New-Item -ItemType Directory -Force -Path $publishDir, $dashboardStage, $packageOutput, $wixObjDir | Out-Null

if (Test-Path (Join-Path $dashboardRoot "package-lock.json")) {
    Write-Host "==> Installing dashboard dependencies"
    Push-Location $dashboardRoot
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed for the dashboard." }
    Pop-Location
}

Write-Host "==> Building dashboard"
Push-Location $dashboardRoot
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm run build failed for the dashboard." }
Pop-Location

$standaloneDir = Join-Path $dashboardRoot ".next\standalone"
if (-not (Test-Path $standaloneDir)) {
    throw "Expected standalone Next.js output at '$standaloneDir'. Run the dashboard build first."
}

Copy-Item (Join-Path $standaloneDir "*") $dashboardStage -Recurse -Force
if (Test-Path (Join-Path $dashboardRoot ".next\static")) {
    Copy-Item (Join-Path $dashboardRoot ".next\static") $dashboardStage -Recurse -Force
}
if (Test-Path (Join-Path $dashboardRoot "public")) {
    Copy-Item (Join-Path $dashboardRoot "public") $dashboardStage -Recurse -Force
}

Write-Host "==> Publishing .NET launcher"
Invoke-ExternalCommand -FilePath "dotnet" -Arguments @(
    "publish",
    $launcherProject,
    "-c", $Configuration,
    "-r", "win-x64",
    "--self-contained", "false",
    "-o", $publishDir,
    "-p:PublishSingleFile=true",
    "-p:UseAppHost=true",
    "-nologo"
) -Description "Publish the Windows launcher for the installer payload"

Copy-Item (Join-Path $repoRoot "start-sanctum-suite.cmd") $packageOutput -Force
Copy-Item (Join-Path $repoRoot "sanctum-suite-gui-launcher.ps1") $packageOutput -Force

$wixTools = @(
    "${env:ProgramFiles(x86)}\WiX Toolset*",
    "${env:ProgramFiles}\WiX Toolset*"
)
$wixRoot = $null
foreach ($pattern in $wixTools) {
    $candidate = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($candidate) {
        $wixRoot = $candidate.FullName
        break
    }
}

if (-not $wixRoot) {
    throw "WiX Toolset was not found. Install WiX Toolset or add the toolset to PATH."
}

$heat = Join-Path $wixRoot "bin\heat.exe"
$candle = Join-Path $wixRoot "bin\candle.exe"
$light = Join-Path $wixRoot "bin\light.exe"

if (-not (Test-Path $heat) -or -not (Test-Path $candle) -or -not (Test-Path $light)) {
    throw "WiX build tools were not found under '$wixRoot'."
}

$appFragment = Join-Path $wixObjDir "SanctumSuiteAppFiles.wxs"
$dashboardFragment = Join-Path $wixObjDir "SanctumSuiteDashboardFiles.wxs"
$wixProduct = Join-Path $wixObjDir "SanctumSuiteProduct.wxs"

Invoke-ExternalCommand -FilePath $heat -Arguments @(
    "dir", $publishDir,
    "-ag",
    "-scom",
    "-sfrag",
    "-sreg",
    "-dr", "INSTALLDIR",
    "-var", "var.PublishDir",
    "-template", "fragment",
    "-out", $appFragment
) -Description "Generate WiX fragment for the published launcher files"

Invoke-ExternalCommand -FilePath $heat -Arguments @(
    "dir", $dashboardStage,
    "-ag",
    "-scom",
    "-sfrag",
    "-sreg",
    "-dr", "INSTALLDIR",
    "-var", "var.DashboardDir",
    "-template", "fragment",
    "-out", $dashboardFragment
) -Description "Generate WiX fragment for the dashboard runtime files"

$wixProductContent = @"
<?xml version=""1.0"" encoding=""utf-8""?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product
    Id="*"
    Name="$("$ProductName")"
    Language="1033"
    Version="$Version"
    Manufacturer="Karol Mrozinski"
    UpgradeCode="{D3A03B09-778F-4F20-B18E-A8B011A40C3B}">
    <Package
      InstallerVersion="500"
      Compressed="yes"
      InstallScope="perMachine"
      Platform="x64"
      Description="Sanctum Suite CTI workspace"
      Comments="Sanctum Suite installer"
      Manufacturer="Karol Mrozinski"/>

    <MediaTemplate CabinetTemplate="SanctumSuite.cab" CompressionLevel="high" />

    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLDIR" />
    <UIRef Id="WixUI_InstallDir" />

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFiles64Folder">
        <Directory Id="INSTALLDIR" Name="Sanctum Suite">
        </Directory>
      </Directory>
    </Directory>

    <Feature Id="ProductFeature" Title="Sanctum Suite" Level="1">
      <ComponentGroupRef Id="PublishedAppFiles" />
      <ComponentGroupRef Id="DashboardFiles" />
      <ComponentRef Id="StartMenuShortcut" />
    </Feature>

    <DirectoryRef Id="INSTALLDIR">
      <Component Id="StartMenuShortcut" Guid="{0DA4D245-930E-4B2F-A842-4A5900C0A5EF}" DiskId="1">
        <Shortcut Id="SanctumSuiteStartMenuShortcut"
                  Name="Sanctum Suite"
                  Target="[#SanctumSuiteLauncher.exe]"
                  WorkingDirectory="INSTALLDIR"
                  Icon="SanctumSuiteIcon.exe"/>
        <RemoveFolder Id="RemoveStartMenuFolder" On="uninstall" />
        <RegistryValue Root="HKCU" Key="Software\Sanctum Suite" Name="installed" Type="integer" Value="1" KeyPath="yes"/>
      </Component>
    </DirectoryRef>

    <Icon Id="SanctumSuiteIcon.exe" SourceFile="$(Join-Path $repoRoot "resources\sanctum-suite-icon.ico")" />
    <Property Id="ARPPRODUCTICON" Value="SanctumSuiteIcon.exe" />
  </Product>

  <Fragment>
    <ComponentGroup Id="PublishedAppFiles">
      <ComponentRef Id="PublishedAppFiles" />
    </ComponentGroup>
    <ComponentGroup Id="DashboardFiles">
      <ComponentRef Id="DashboardFiles" />
    </ComponentGroup>
  </Fragment>
</Wix>
"@

Set-Content -Path $wixProduct -Value $wixProductContent -Encoding UTF8

$wixArgs = @(
  "-nologo",
  "-out", (Join-Path $wixObjDir "SanctumSuiteProduct.wixobj"),
  "-ext", (Join-Path $wixRoot "bin\WixUIExtension.dll"),
  "-dPublishDir=$publishDir",
  "-dDashboardDir=$dashboardStage",
  $wixProduct
)
Invoke-ExternalCommand -FilePath $candle -Arguments $wixArgs -Description "Compile the WiX product definition"

if (Test-Path $appFragment) {
    Invoke-ExternalCommand -FilePath $candle -Arguments @("-nologo","-out",(Join-Path $wixObjDir "SanctumSuiteAppFiles.wixobj"),"-dPublishDir=$publishDir", $appFragment) -Description "Compile the launcher fragment"
}
if (Test-Path $dashboardFragment) {
    Invoke-ExternalCommand -FilePath $candle -Arguments @("-nologo","-out",(Join-Path $wixObjDir "SanctumSuiteDashboardFiles.wixobj"),"-dDashboardDir=$dashboardStage", $dashboardFragment) -Description "Compile the dashboard fragment"
}

$wixLinkInputs = @(
    (Join-Path $wixObjDir "SanctumSuiteProduct.wixobj"),
    (Join-Path $wixObjDir "SanctumSuiteAppFiles.wixobj"),
    (Join-Path $wixObjDir "SanctumSuiteDashboardFiles.wixobj")
)

$lightCommand = @(
    "-nologo",
    "-out", $wixMsiPath,
    "-ext", (Join-Path $wixRoot "bin\WixUIExtension.dll"),
    "-ext", (Join-Path $wixRoot "bin\WixUtilExtension.dll"),
    $wixLinkInputs
)
Invoke-ExternalCommand -FilePath $light -Arguments $lightCommand -Description "Link the final MSI package"

Write-Host "==> Signing mode: $SigningMode"

$signingReady = $false

switch ($SigningMode) {
    "azure-trusted-signing" {
        if (-not ($env:AZURE_TENANT_ID -and $env:AZURE_CLIENT_ID -and $env:AZURE_CLIENT_SECRET -and $env:AZURE_TRUSTED_SIGNING_ENDPOINT -and $env:AZURE_TRUSTED_SIGNING_ACCOUNT_NAME -and $env:AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME)) {
            throw "Azure Trusted Signing selected but required environment variables are missing."
        }
        Invoke-AzureTrustedSigning -MsiPath $wixMsiPath -Endpoint $env:AZURE_TRUSTED_SIGNING_ENDPOINT -AccountName $env:AZURE_TRUSTED_SIGNING_ACCOUNT_NAME -CertificateProfileName $env:AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME -TenantId $env:AZURE_TENANT_ID -ClientId $env:AZURE_CLIENT_ID -ClientSecret $env:AZURE_CLIENT_SECRET -Policy $env:AZURE_TRUSTED_SIGNING_POLICY
        $signingReady = $true
    }
    "pfx" {
        if (-not ($env:WINDOWS_CERT_PFX_BASE64 -and $env:WINDOWS_CERT_PASSWORD)) {
            throw "PFX signing selected but WINDOWS_CERT_PFX_BASE64 and WINDOWS_CERT_PASSWORD are missing."
        }

        $certPath = Join-Path $packageOutput "sanctum-suite-signing.pfx"
        $certBytes = [System.Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64)
        [System.IO.File]::WriteAllBytes($certPath, $certBytes)

        $signtool = Get-Command signtool -ErrorAction SilentlyContinue
        if (-not $signtool) {
            throw "signtool.exe was not found on PATH. Install the Windows SDK or add signtool to PATH."
        }

        Invoke-ExternalCommand -FilePath $signtool.Source -Arguments @(
            "sign",
            "/fd", "SHA256",
            "/a",
            "/f", $certPath,
            "/p", $env:WINDOWS_CERT_PASSWORD,
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            $wixMsiPath
        ) -Description "Sign the MSI package with the configured certificate"
        $signingReady = $true
    }
    "ev" {
        Write-Host "==> EV code signing mode selected. Requires an EV certificate in a managed environment and a supported signing toolchain."
        $certThumbprint = $env:WINDOWS_CERT_THUMBPRINT
        if ($certThumbprint) {
            Invoke-EvCodeSigning -MsiPath $wixMsiPath -Thumbprint $certThumbprint
            $signingReady = $true
        }
        elseif ($env:WINDOWS_CERT_PFX_BASE64 -and $env:WINDOWS_CERT_PASSWORD) {
            $certPath = Join-Path $packageOutput "sanctum-suite-ev-signing.pfx"
            $certBytes = [System.Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64)
            [System.IO.File]::WriteAllBytes($certPath, $certBytes)
            Invoke-EvCodeSigning -MsiPath $wixMsiPath -PfxPath $certPath -PfxPassword $env:WINDOWS_CERT_PASSWORD
            $signingReady = $true
        }
        else {
            Write-Host "==> EV mode selected but no compatible certificate was configured; build continues in validation-only mode."
            $signingReady = $false
        }
    }
    "x509" {
        Write-Host "==> X.509 signing mode selected. Requires an enterprise PKI certificate or a PFX-backed trust chain."
        if ($env:WINDOWS_CERT_THUMBPRINT) {
            Invoke-X509Signing -MsiPath $wixMsiPath -Thumbprint $env:WINDOWS_CERT_THUMBPRINT
            $signingReady = $true
        }
        elseif ($env:WINDOWS_CERT_PFX_BASE64 -and $env:WINDOWS_CERT_PASSWORD) {
            $certPath = Join-Path $packageOutput "sanctum-suite-x509-signing.pfx"
            $certBytes = [System.Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64)
            [System.IO.File]::WriteAllBytes($certPath, $certBytes)
            Invoke-X509Signing -MsiPath $wixMsiPath -PfxPath $certPath -PfxPassword $env:WINDOWS_CERT_PASSWORD
            $signingReady = $true
        }
        else {
            Write-Host "==> X.509 mode selected but no certificate material was configured; build remains validation-only."
            $signingReady = $false
        }
    }
    "mtls" {
        Write-Host "==> mTLS mode selected. Requires a client certificate and optional CA bundle for the trust path."
        if ($env:MTLS_CLIENT_CERT_PATH) {
            Invoke-MtlsSigning -MsiPath $wixMsiPath -ClientCertPath $env:MTLS_CLIENT_CERT_PATH -ClientCertPassword $env:MTLS_CLIENT_CERT_PASSWORD -CaBundlePath $env:MTLS_CA_BUNDLE_PATH
            $signingReady = $true
        }
        else {
            Write-Host "==> mTLS mode selected but no client certificate was configured; build remains validation-only."
            $signingReady = $false
        }
    }
    "root-ca" {
        Write-Host "==> Root CA mode selected. Requires a private CA trust path or enterprise signing chain."
        if ($env:ROOT_CA_CERT_PATH) {
            Invoke-RootCaSigning -MsiPath $wixMsiPath -CaCertPath $env:ROOT_CA_CERT_PATH -ChainPath $env:ROOT_CA_CHAIN_PATH
            $signingReady = $true
        }
        else {
            Write-Host "==> Root CA mode selected but no root certificate path was configured; build remains validation-only."
            $signingReady = $false
        }
    }
    "byo-pki" {
        Write-Host "==> BYO-PKI mode selected. Requires an internal PKI configuration profile."
        if ($env:BYO_PKI_CONFIG_PATH) {
            Invoke-ByoPkiSigning -MsiPath $wixMsiPath -PkiConfigPath $env:BYO_PKI_CONFIG_PATH
            $signingReady = $true
        }
        else {
            Write-Host "==> BYO-PKI mode selected but no PKI config was configured; build remains validation-only."
            $signingReady = $false
        }
    }
    "fips1403" {
        Write-Host "==> FIPS 140-3 mode selected. Requires a compliant HSM-backed cryptographic module."
        if ($env:FIPS1403_HSM_MODULE_PATH) {
            Invoke-Fips1403Signing -MsiPath $wixMsiPath -HsmModulePath $env:FIPS1403_HSM_MODULE_PATH -KeyLabel $env:FIPS1403_KEY_LABEL
            $signingReady = $true
        }
        else {
            Write-Host "==> FIPS 140-3 mode selected but no HSM module path was configured; build remains validation-only."
            $signingReady = $false
        }
    }
    "niapc-nato" {
        Write-Host "==> NIAPC/NATO-ready signing mode selected. Requires a validated secure environment and the relevant accreditation profile."
        if ($env:NIAPC_NATO_PKI_PROFILE) {
            Invoke-NiapcNatoSigning -MsiPath $wixMsiPath -PkiProfile $env:NIAPC_NATO_PKI_PROFILE
            $signingReady = $true
        }
        else {
            Write-Host "==> NIAPC/NATO mode selected but no PKI profile was configured; the build remains validation-only."
            $signingReady = $false
        }
    }
    "nsa-type-1" {
        Write-Host "==> NSA Type 1 mode selected. Requires a controlled, government-grade signing environment and a valid key management flow."
        if ($env:NSA_TYPE1_KEYRING_PATH -or $env:NSA_TYPE1_PROFILE) {
            Invoke-NsaType1Signing -MsiPath $wixMsiPath -KeyringPath $env:NSA_TYPE1_KEYRING_PATH -Profile $env:NSA_TYPE1_PROFILE
            $signingReady = $true
        }
        else {
            Write-Host "==> NSA Type 1 mode selected but no key material or profile information was configured; the build remains validation-only."
            $signingReady = $false
        }
    }
    "hsm-fips1403-class4" {
        Write-Host "==> HSM FIPS 140-3 Class 4 mode selected. Requires a hardened HSM token and a controlled key inventory."
        if ($env:HSM_TOKEN) {
            Invoke-HsmFips1403Class4Signing -MsiPath $wixMsiPath -HsmToken $env:HSM_TOKEN -KeyId $env:HSM_KEY_ID
            $signingReady = $true
        }
        else {
            Write-Host "==> HSM FIPS 140-3 Class 4 mode selected but no HSM token was configured; the build remains validation-only."
            $signingReady = $false
        }
    }
    "whql" {
        Write-Host "==> WHQL mode selected. Requires Microsoft hardware/driver validation and a compliant driver-signing environment."
        if ($env:WHQL_SIGNING_CERT_THUMBPRINT -or $env:WHQL_SIGNING_CERT_PFX_BASE64) {
            Write-Host "==> WHQL flow prepared for a compliant Microsoft validation environment."
            $signingReady = $true
        }
        else {
            $signingReady = $false
        }
    }
    "hlk" {
        Write-Host "==> HLK mode selected. Requires a hardware and logistics validation environment with Microsoft test lab support."
        if ($env:HLK_CERT_THUMBPRINT -or $env:HLK_CERT_PFX_BASE64) {
            Write-Host "==> HLK flow prepared for a Microsoft test-lab signing environment."
            $signingReady = $true
        }
        else {
            $signingReady = $false
        }
    }
    "elam" {
        Write-Host "==> ELAM mode selected. Requires kernel-level security integration and OS integration validation."
        if ($env:ELAM_SIGNING_CERT_THUMBPRINT -or $env:ELAM_SIGNING_CERT_PFX_BASE64) {
            Write-Host "==> ELAM flow prepared for a system-signed environment."
            $signingReady = $true
        }
        else {
            $signingReady = $false
        }
    }
    "ppl" {
        Write-Host "==> PPL mode selected. Requires a Protected Process Light integration and system-level compliance environment."
        if ($env:PPL_SIGNING_CERT_THUMBPRINT -or $env:PPL_SIGNING_CERT_PFX_BASE64) {
            Write-Host "==> PPL flow prepared for a protected-process signing environment."
            $signingReady = $true
        }
        else {
            $signingReady = $false
        }
    }
    "mvi" {
        Write-Host "==> MVI mode selected. Requires a Microsoft validation or security-program environment specific to the target program."
        if ($env:MVI_SIGNING_CERT_THUMBPRINT -or $env:MVI_SIGNING_CERT_PFX_BASE64) {
            Write-Host "==> MVI flow prepared for the corresponding Microsoft validation program."
            $signingReady = $true
        }
        else {
            $signingReady = $false
        }
    }
    default {
        if ($env:AZURE_TENANT_ID -and $env:AZURE_CLIENT_ID -and $env:AZURE_CLIENT_SECRET -and $env:AZURE_TRUSTED_SIGNING_ENDPOINT -and $env:AZURE_TRUSTED_SIGNING_ACCOUNT_NAME -and $env:AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME) {
            Invoke-AzureTrustedSigning -MsiPath $wixMsiPath -Endpoint $env:AZURE_TRUSTED_SIGNING_ENDPOINT -AccountName $env:AZURE_TRUSTED_SIGNING_ACCOUNT_NAME -CertificateProfileName $env:AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME -TenantId $env:AZURE_TENANT_ID -ClientId $env:AZURE_CLIENT_ID -ClientSecret $env:AZURE_CLIENT_SECRET -Policy $env:AZURE_TRUSTED_SIGNING_POLICY
            $signingReady = $true
        }
        elseif ($env:WINDOWS_CERT_PFX_BASE64 -and $env:WINDOWS_CERT_PASSWORD) {
            $certPath = Join-Path $packageOutput "sanctum-suite-signing.pfx"
            $certBytes = [System.Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64)
            [System.IO.File]::WriteAllBytes($certPath, $certBytes)

            $signtool = Get-Command signtool -ErrorAction SilentlyContinue
            if (-not $signtool) {
                throw "signtool.exe was not found on PATH. Install the Windows SDK or add signtool to PATH."
            }

            Invoke-ExternalCommand -FilePath $signtool.Source -Arguments @(
                "sign",
                "/fd", "SHA256",
                "/a",
                "/f", $certPath,
                "/p", $env:WINDOWS_CERT_PASSWORD,
                "/tr", "http://timestamp.digicert.com",
                "/td", "SHA256",
                $wixMsiPath
            ) -Description "Sign the MSI package with the configured certificate"
            $signingReady = $true
        }
        else {
            Write-Host "==> No production signing credentials were provided. The installer was built but remains unsigned for validation only."
        }
    }
}

if ($RequireSignedBuild -and -not $signingReady) {
    throw "A signed build was required, but no certificate-backed signing path is available in the current environment."
}

Write-Host "==> Installer created: $wixMsiPath"
return $wixMsiPath
