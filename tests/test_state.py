from cascade.state.store import Store
from cascade.state.app_state import AppState

def test_store_get_set():
    store = Store()
    state = store.get_state()
    assert isinstance(state, AppState)

def test_store_subscribe():
    store = Store()
    changes = []
    store.subscribe(lambda s: changes.append(s))
    
    # Update state immutably
    store.set_state(lambda prev: prev.with_update(is_loading=True))
    
    assert len(changes) == 1
    assert changes[0].is_loading is True

def test_store_unsubscribe():
    store = Store()
    changes = []
    unsub = store.subscribe(lambda s: changes.append(s))
    unsub()
    
    store.set_state(lambda prev: prev.with_update(is_loading=True))
    assert len(changes) == 0
