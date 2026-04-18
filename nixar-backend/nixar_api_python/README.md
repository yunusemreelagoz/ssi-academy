# Nixar API Python

## 📌 Definition
This repository provides Python bindings for Nixar along with several demo applications. These demos can be executed either within a Docker container or directly on your operating system. Nixar supports three types of wallets: JSON, SQLite, and PostgreSQL, which are specified when creating an agent.

```python
# JSON Wallet
nixar_agent = Nixar(name, password, role)

# SQLite Wallet
nixar_agent = Nixar(name, password, role, None, "sqlite")

# PostgreSQL Wallet
nixar_agent = Nixar(name, password, role, None, "pgsql", DB_HOST, DB_USERNAME, DB_PASSWORD)
```

📢 **Note:** If PostgreSQL is used as the wallet, the database must be running and must contain a database with the same name as the agent.

## ⚙️ Requirements
- Python 3
- [cffi](https://cffi.readthedocs.io/en/latest/goals.html)
- Nixar core library:
  - Download the appropriate Nixar core library for your operating system from [bag.org.tr](https://proje.bag.org.tr/nixar_shared).
  - Export the library path:
    ```sh
    export DYLD_LIBRARY_PATH=$(pwd)
    ```

## 🚀 Running with Docker

Before building, specify which demo should run in the `x86_64.dockerfile`.

### 1️⃣ Build the Docker Image
```sh
docker build -t demo-w-pgsql -f x86_64.dockerfile .
```

### 2️⃣ Run the Demo Inside Docker
To execute a specific script, use the following command:
```sh
docker run -v ./.tmp:/agent/.tmp demo-w-pgsql
```

## 📜 Release Notes
### v0.3.2 - Initial Release
### v1.0.0 - Release
- Create agent function moved to [the Nixar constructor](nixar/nixar_api.py)
- Integrated Zula SQL Storage.
  - JSON(Default)
  - SQLite
  - PostgreSQL
- Added functionality for updating Zula passwords.
- Added Tag variable to the create credential definition
```python
  def issuer_create_credential_definition(self, schema_id: str, is_revocable: bool, tag: str,
                                          issuance_type=CredDefIssuanceType.ISSUANCE_BY_DEFAULT,
                                          max_cred_num=1000) -> dict:
```


## 🔥 Additional Notes
- You can use [von-network](https://github.com/bcgov/von-network) as a ledger.

---

Happy Coding! 🚀

