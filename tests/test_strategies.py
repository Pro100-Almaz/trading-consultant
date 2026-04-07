"""
TDD — стратегии пользователя.

Покрываем:
  - Репозиторий: CRUD + эксклюзивность тикеров
  - API: POST, GET, PUT, DELETE + авторизация
"""
import pytest

from tests.conftest import AUTH_HEADERS, USER_ID


# ---------------------------------------------------------------------------
# Репозиторий
# ---------------------------------------------------------------------------

class TestStrategyRepository:
    def test_create_returns_strategy(self, db):
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        s = repo.create(
            user_id=USER_ID,
            name="Growth",
            description="Tech stocks",
            icon="trending_up",
            color="#22C55E",
            symbols=["NVDA", "TSLA"],
        )
        assert s.id is not None
        assert s.name == "Growth"
        assert s.user_id == USER_ID
        assert s.symbols == ["NVDA", "TSLA"]

    def test_get_by_user_returns_only_own(self, db):
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        repo.create(user_id=USER_ID, name="A", symbols=["AAPL"])
        repo.create(user_id="other-user", name="B", symbols=["GOOG"])

        result = repo.get_by_user(USER_ID)
        assert len(result) == 1
        assert result[0].name == "A"

    def test_get_by_id(self, db):
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        created = repo.create(user_id=USER_ID, name="X", symbols=[])
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    def test_update_changes_fields(self, db):
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        s = repo.create(user_id=USER_ID, name="Old", symbols=["AAPL"])
        updated = repo.update(s, name="New", symbols=["TSLA"])
        assert updated.name == "New"
        assert updated.symbols == ["TSLA"]

    def test_delete_removes_strategy(self, db):
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        s = repo.create(user_id=USER_ID, name="ToDelete", symbols=[])
        repo.delete(s)
        assert repo.get_by_id(s.id) is None

    def test_symbols_exclusive_across_strategies(self, db):
        """Тикер AAPL переходит из стратегии A в B — из A должен исчезнуть."""
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        a = repo.create(user_id=USER_ID, name="A", symbols=["AAPL", "TSLA"])
        b = repo.create(user_id=USER_ID, name="B", symbols=[])

        # Добавляем AAPL в B → AAPL уходит из A
        repo.assign_symbols_exclusive(user_id=USER_ID, target_id=b.id, symbols=["AAPL"])

        db.refresh(a)
        db.refresh(b)
        assert "AAPL" not in a.symbols
        assert "AAPL" in b.symbols
        assert "TSLA" in a.symbols  # TSLA остаётся в A

    def test_symbols_exclusive_not_affects_other_users(self, db):
        """Эксклюзивность только в рамках одного user_id."""
        from app.repositories.strategy_repository import StrategyRepository
        repo = StrategyRepository(db)
        my = repo.create(user_id=USER_ID, name="Mine", symbols=["AAPL"])
        other = repo.create(user_id="other-user", name="Other", symbols=["AAPL"])

        # Переназначаем AAPL внутри USER_ID
        new_s = repo.create(user_id=USER_ID, name="New", symbols=[])
        repo.assign_symbols_exclusive(user_id=USER_ID, target_id=new_s.id, symbols=["AAPL"])

        db.refresh(my)
        db.refresh(other)
        assert "AAPL" not in my.symbols
        assert "AAPL" in other.symbols  # другой пользователь не тронут


# ---------------------------------------------------------------------------
# API — POST /strategies
# ---------------------------------------------------------------------------

class TestCreateStrategy:
    def test_create_success(self, client):
        resp = client.post("/strategies", json={
            "name": "Growth",
            "description": "Tech stocks",
            "icon": "trending_up",
            "color": "#22C55E",
            "symbols": ["NVDA", "TSLA"],
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Growth"
        assert data["symbols"] == ["NVDA", "TSLA"]
        assert "id" in data
        assert "created_at" in data

    def test_create_minimal(self, client):
        """Только name — остальное по умолчанию."""
        resp = client.post("/strategies", json={"name": "Simple"}, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["symbols"] == []
        assert data["description"] == ""
        assert data["icon"] == "pie_chart"
        assert data["color"] == "#6366F1"

    def test_create_no_auth(self, client):
        resp = client.post("/strategies", json={"name": "X"})
        assert resp.status_code == 401

    def test_create_name_required(self, client):
        resp = client.post("/strategies", json={"description": "no name"}, headers=AUTH_HEADERS)
        assert resp.status_code == 422

    def test_create_name_too_long(self, client):
        resp = client.post("/strategies", json={"name": "A" * 101}, headers=AUTH_HEADERS)
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "nameTooLong"

    def test_create_symbols_become_exclusive(self, client):
        """Создаём стратегию A с AAPL, потом B с AAPL — AAPL уходит из A."""
        client.post("/strategies", json={"name": "A", "symbols": ["AAPL"]}, headers=AUTH_HEADERS)
        client.post("/strategies", json={"name": "B", "symbols": ["AAPL"]}, headers=AUTH_HEADERS)

        resp = client.get("/strategies", headers=AUTH_HEADERS)
        strategies = resp.json()
        a = next(s for s in strategies if s["name"] == "A")
        b = next(s for s in strategies if s["name"] == "B")
        assert "AAPL" not in a["symbols"]
        assert "AAPL" in b["symbols"]


# ---------------------------------------------------------------------------
# API — GET /strategies
# ---------------------------------------------------------------------------

class TestGetStrategies:
    def test_get_empty(self, client):
        resp = client.get("/strategies", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_returns_own_only(self, client):
        client.post("/strategies", json={"name": "Mine"}, headers=AUTH_HEADERS)
        resp = client.get("/strategies", headers=AUTH_HEADERS)
        assert len(resp.json()) == 1

    def test_get_no_auth(self, client):
        resp = client.get("/strategies")
        assert resp.status_code == 401

    def test_get_sorted_by_created_at(self, client):
        client.post("/strategies", json={"name": "First"}, headers=AUTH_HEADERS)
        client.post("/strategies", json={"name": "Second"}, headers=AUTH_HEADERS)
        strategies = client.get("/strategies", headers=AUTH_HEADERS).json()
        assert strategies[0]["name"] == "First"
        assert strategies[1]["name"] == "Second"


# ---------------------------------------------------------------------------
# API — PUT /strategies/{id}
# ---------------------------------------------------------------------------

class TestUpdateStrategy:
    def _create(self, client, name="Test", symbols=None):
        resp = client.post("/strategies", json={
            "name": name,
            "symbols": symbols or [],
        }, headers=AUTH_HEADERS)
        return resp.json()

    def test_update_name(self, client):
        s = self._create(client, "Old")
        resp = client.put(f"/strategies/{s['id']}", json={"name": "New"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_update_symbols(self, client):
        s = self._create(client, symbols=["AAPL"])
        resp = client.put(f"/strategies/{s['id']}", json={"symbols": ["TSLA"]}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["symbols"] == ["TSLA"]

    def test_update_partial(self, client):
        """Передаём только color — name не меняется."""
        s = self._create(client, "Keep")
        resp = client.put(f"/strategies/{s['id']}", json={"color": "#FF0000"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Keep"
        assert resp.json()["color"] == "#FF0000"

    def test_update_not_found(self, client):
        resp = client.put("/strategies/nonexistent-id", json={"name": "X"}, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_update_no_auth(self, client):
        s = self._create(client)
        resp = client.put(f"/strategies/{s['id']}", json={"name": "X"})
        assert resp.status_code == 401

    def test_update_forbidden(self, client):
        """Другой пользователь не может редактировать чужую стратегию."""
        s = self._create(client)
        other_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJ1c2VyX2lkIjoib3RoZXItdXNlciIsInN1YiI6Im90aGVyLXVzZXIifQ"
            ".signature_not_verified"
        )
        resp = client.put(
            f"/strategies/{s['id']}",
            json={"name": "Hack"},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    def test_update_symbols_exclusive(self, client):
        """При PUT с символами — эксклюзивность соблюдается."""
        a = self._create(client, "A", ["AAPL", "TSLA"])
        b = self._create(client, "B", [])
        client.put(f"/strategies/{b['id']}", json={"symbols": ["AAPL"]}, headers=AUTH_HEADERS)

        strategies = client.get("/strategies", headers=AUTH_HEADERS).json()
        a_updated = next(s for s in strategies if s["name"] == "A")
        b_updated = next(s for s in strategies if s["name"] == "B")
        assert "AAPL" not in a_updated["symbols"]
        assert "AAPL" in b_updated["symbols"]


# ---------------------------------------------------------------------------
# API — DELETE /strategies/{id}
# ---------------------------------------------------------------------------

class TestDeleteStrategy:
    def _create(self, client, name="Test"):
        return client.post("/strategies", json={"name": name}, headers=AUTH_HEADERS).json()

    def test_delete_success(self, client):
        s = self._create(client)
        resp = client.delete(f"/strategies/{s['id']}", headers=AUTH_HEADERS)
        assert resp.status_code == 204

        strategies = client.get("/strategies", headers=AUTH_HEADERS).json()
        assert not any(x["id"] == s["id"] for x in strategies)

    def test_delete_not_found(self, client):
        resp = client.delete("/strategies/nonexistent-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_delete_no_auth(self, client):
        s = self._create(client)
        resp = client.delete(f"/strategies/{s['id']}")
        assert resp.status_code == 401

    def test_delete_forbidden(self, client):
        s = self._create(client)
        other_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJ1c2VyX2lkIjoib3RoZXItdXNlciIsInN1YiI6Im90aGVyLXVzZXIifQ"
            ".signature_not_verified"
        )
        resp = client.delete(
            f"/strategies/{s['id']}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    def test_delete_does_not_affect_positions(self, client):
        """Удаление стратегии — позиции не трогаем. Проверяем косвенно:
        тикеры из удалённой стратегии можно добавить в новую."""
        s = self._create(client)
        client.put(f"/strategies/{s['id']}", json={"symbols": ["AAPL"]}, headers=AUTH_HEADERS)
        client.delete(f"/strategies/{s['id']}", headers=AUTH_HEADERS)

        new_resp = client.post("/strategies", json={"name": "New", "symbols": ["AAPL"]}, headers=AUTH_HEADERS)
        assert new_resp.status_code == 201
        assert "AAPL" in new_resp.json()["symbols"]
