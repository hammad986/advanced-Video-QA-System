from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import sys


class CredentialStoreError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class _CredentialW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class LocalCredentialStore:
    _PREFIX = "dpapi:"
    _WINCRED_PREFIX = "wincred:"
    _TARGET_PREFIX = "AdvancedVideoQAPro/provider/"
    _CRED_TYPE_GENERIC = 1
    _CRED_PERSIST_LOCAL_MACHINE = 2

    def encrypt(self, secret: str) -> str:
        if not secret:
            return ""
        if sys.platform != "win32":
            raise CredentialStoreError("Encrypted provider keys require Windows DPAPI.")
        payload = secret.encode("utf-8")
        encrypted = self._protect(payload)
        return f"{self._PREFIX}{base64.b64encode(encrypted).decode('ascii')}"

    def decrypt(self, encrypted_secret: str) -> str:
        if not encrypted_secret:
            return ""
        if not encrypted_secret.startswith(self._PREFIX):
            raise CredentialStoreError("Provider key is not stored in the expected encrypted format.")
        if sys.platform != "win32":
            raise CredentialStoreError("Encrypted provider keys require Windows DPAPI.")
        payload = base64.b64decode(encrypted_secret.removeprefix(self._PREFIX))
        return self._unprotect(payload).decode("utf-8")

    def store_secret(self, target_id: str, secret: str) -> str:
        if not secret:
            return ""
        target_name = self._target_name(target_id)
        protected_secret = self.encrypt(secret)
        try:
            self._write_windows_credential(target_name, protected_secret)
            return f"{self._WINCRED_PREFIX}{target_name}"
        except CredentialStoreError:
            return protected_secret

    def retrieve_secret(self, stored_reference: str) -> str:
        if not stored_reference:
            return ""
        if stored_reference.startswith(self._WINCRED_PREFIX):
            target_name = stored_reference.removeprefix(self._WINCRED_PREFIX)
            protected_secret = self._read_windows_credential(target_name)
            return self.decrypt(protected_secret)
        return self.decrypt(stored_reference)

    def delete_secret(self, stored_reference: str) -> None:
        if not stored_reference.startswith(self._WINCRED_PREFIX):
            return
        target_name = stored_reference.removeprefix(self._WINCRED_PREFIX)
        self._delete_windows_credential(target_name)

    def _target_name(self, target_id: str) -> str:
        safe_target = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in target_id)
        return f"{self._TARGET_PREFIX}{safe_target}"

    def _protect(self, payload: bytes) -> bytes:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        in_buffer = ctypes.create_string_buffer(payload)
        in_blob = _DataBlob(len(payload), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        out_blob = _DataBlob()
        if not crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "Advanced Video QA Pro",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            raise CredentialStoreError("Could not encrypt provider key.")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def _unprotect(self, payload: bytes) -> bytes:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        in_buffer = ctypes.create_string_buffer(payload)
        in_blob = _DataBlob(len(payload), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        out_blob = _DataBlob()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            raise CredentialStoreError("Could not decrypt provider key.")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def _write_windows_credential(self, target_name: str, protected_secret: str) -> None:
        if sys.platform != "win32":
            raise CredentialStoreError("Windows Credential Manager requires Windows.")
        advapi32 = ctypes.windll.advapi32
        payload = protected_secret.encode("utf-16-le")
        payload_buffer = ctypes.create_string_buffer(payload)
        credential = _CredentialW(
            0,
            self._CRED_TYPE_GENERIC,
            target_name,
            "Advanced Video QA Pro provider credential",
            wintypes.FILETIME(),
            len(payload),
            ctypes.cast(payload_buffer, ctypes.POINTER(ctypes.c_ubyte)),
            self._CRED_PERSIST_LOCAL_MACHINE,
            0,
            None,
            None,
            "AdvancedVideoQAPro",
        )
        if not advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise CredentialStoreError("Could not write provider key to Windows Credential Manager.")

    def _read_windows_credential(self, target_name: str) -> str:
        if sys.platform != "win32":
            raise CredentialStoreError("Windows Credential Manager requires Windows.")
        advapi32 = ctypes.windll.advapi32
        credential_pointer = ctypes.POINTER(_CredentialW)()
        if not advapi32.CredReadW(
            target_name,
            self._CRED_TYPE_GENERIC,
            0,
            ctypes.byref(credential_pointer),
        ):
            raise CredentialStoreError("Could not read provider key from Windows Credential Manager.")
        try:
            credential = credential_pointer.contents
            payload = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return payload.decode("utf-16-le")
        finally:
            advapi32.CredFree(credential_pointer)

    def _delete_windows_credential(self, target_name: str) -> None:
        if sys.platform != "win32":
            return
        advapi32 = ctypes.windll.advapi32
        advapi32.CredDeleteW(target_name, self._CRED_TYPE_GENERIC, 0)
