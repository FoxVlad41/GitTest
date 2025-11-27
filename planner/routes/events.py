from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select, Session
from typing import List

event_router = APIRouter()

# CREATE
@event_router.post("/new")
async def create_event(new_event: Event, session: Session = Depends(get_session)):
    session.add(new_event)
    session.commit()
    session.refresh(new_event)
    return {"message": "Event created successfully"}

# READ ALL
@event_router.get("/", response_model=list[Event])
async def retrieve_all_events(session: Session = Depends(get_session)):
    statement = select(Event)
    events = session.exec(statement).all()
    return events

# READ ONE
@event_router.get("/{id}", response_model=Event)
async def retrieve_event(id: int, session: Session = Depends(get_session)):
    event = session.get(Event, id)
    if event:
        return event
    raise HTTPException(status_code=404, detail="Event not found")

# UPDATE
@event_router.put("/edit/{id}", response_model=Event)
async def update_event(id: int, new_data: Event, session: Session = Depends(get_session)):
    event = session.get(Event, id)
    if event:
        for key, value in new_data.dict(exclude_unset=True).items():
            setattr(event, key, value)
        session.commit()
        session.refresh(event)
        return event
    raise HTTPException(status_code=404, detail="Event not found")

# DELETE
@event_router.delete("/delete/{id}")
async def delete_event(id: int, session: Session = Depends(get_session)):
    event = session.get(Event, id)
    if event:
        session.delete(event)
        session.commit()
        return {"message": "Event deleted successfully"}
    raise HTTPException(status_code=404, detail="Event not found")
