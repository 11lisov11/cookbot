def test_recipes_preflight_and_run(client):
    listed = client.get("/recipes")
    assert listed.status_code == 200
    recipe_ids = {recipe["id"] for recipe in listed.json()}
    assert {"dry_run_stir_demo", "supervised_scrambled_eggs"} <= recipe_ids

    before_home = client.post("/recipes/dry_run_stir_demo/preflight")
    assert before_home.status_code == 200
    assert before_home.json()["ok"] is False
    assert "not_homed" in before_home.json()["reasons"]

    assert client.post("/home").status_code == 200
    preflight = client.post("/recipes/dry_run_stir_demo/preflight")
    assert preflight.status_code == 200
    assert preflight.json()["ok"] is True

    run = client.post("/recipes/dry_run_stir_demo/run")
    assert run.status_code == 200
    assert run.json()["accepted"] is True
    assert run.json()["executed_steps"] == 5


def test_locked_recipe_does_not_run(client):
    assert client.post("/home").status_code == 200
    preflight = client.post("/recipes/supervised_scrambled_eggs/preflight")
    assert preflight.status_code == 200
    assert preflight.json()["ok"] is False
    assert "recipe_locked" in preflight.json()["reasons"]

    run = client.post("/recipes/supervised_scrambled_eggs/run")
    assert run.status_code == 200
    assert run.json()["accepted"] is False
    assert "recipe_locked" in run.json()["rejected_reason"]

