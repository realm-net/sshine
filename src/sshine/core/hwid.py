from __future__ import annotations

import base64
import hashlib
import platform
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path

import keyring

from sshine.const import KEYRING_SERVICE_NAME


@dataclass(frozen=True)
class HWIDManager:
    unique_key_name: str = "verification.uniqueKey"
    kdf_salt_name: str = "verification.kdfSalt"

    def get_hwid(self) -> str:
        unique_key = self._get_or_create_unique_key()
        machine_fingerprint = self._get_machine_fingerprint()

        payload = f"{machine_fingerprint}:{unique_key}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_encryption_key(self) -> bytes:
        """
        Returns a 32-byte encryption key derived from the current HWID.

        Use this key for AES-256-GCM / ChaCha20-Poly1305 / SQLCipher keying.
        Do not store it on disk.
        """
        hwid = self.get_hwid()
        salt = self._get_or_create_kdf_salt()

        return hashlib.scrypt(
            password=hwid.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )

    def get_encryption_key_b64(self) -> str:
        return base64.urlsafe_b64encode(self.get_encryption_key()).decode("ascii")

    def _get_or_create_unique_key(self) -> str:
        existing_key = keyring.get_password(KEYRING_SERVICE_NAME, self.unique_key_name)

        if existing_key:
            return existing_key

        unique_key = secrets.token_urlsafe(64)
        keyring.set_password(KEYRING_SERVICE_NAME, self.unique_key_name, unique_key)

        return unique_key

    def _get_or_create_kdf_salt(self) -> bytes:
        existing_salt = keyring.get_password(KEYRING_SERVICE_NAME, self.kdf_salt_name)

        if existing_salt:
            return base64.b64decode(existing_salt.encode("ascii"))

        salt = secrets.token_bytes(16)

        keyring.set_password(
            KEYRING_SERVICE_NAME,
            self.kdf_salt_name,
            base64.b64encode(salt).decode("ascii"),
        )

        return salt

    def _get_machine_fingerprint(self) -> str:
        parts = [
            platform.system(),
            platform.node(),
            platform.machine(),
            self._get_platform_machine_id(),
        ]

        clean_parts = [part.strip() for part in parts if part and part.strip()]
        raw_fingerprint = "|".join(clean_parts)

        return hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()

    def _get_platform_machine_id(self) -> str:
        system = platform.system().lower()

        if system == "windows":
            return self._get_windows_machine_guid()

        if system == "linux":
            return self._read_first_existing_file(
                "/etc/machine-id",
                "/var/lib/dbus/machine-id",
            )

        if system == "darwin":
            return self._get_macos_platform_uuid()

        return ""

    def _get_windows_machine_guid(self) -> str:
        try:
            result = subprocess.run(
                [
                    "reg",
                    "query",
                    r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography",
                    "/v",
                    "MachineGuid",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            for line in result.stdout.splitlines():
                if "MachineGuid" in line:
                    return line.split()[-1]

        except Exception:
            return ""

        return ""

    def _get_macos_platform_uuid(self) -> str:
        try:
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                check=True,
            )

            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split("=")[-1].strip().strip('"')

        except Exception:
            return ""

        return ""

    def _read_first_existing_file(self, *paths: str) -> str:
        for path in paths:
            p = Path(path)
            if not p.exists():
                continue
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                continue
        return ""
