package com.example.reminderapp

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ReminderAdapter(private var reminders: MutableList<String>) :
    RecyclerView.Adapter<ReminderAdapter.ReminderViewHolder>() {

    class ReminderViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textViewReminder: TextView = itemView.findViewById(R.id.textViewReminder)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ReminderViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_reminder, parent, false)
        return ReminderViewHolder(view)
    }

    override fun onBindViewHolder(holder: ReminderViewHolder, position: Int) {
        holder.textViewReminder.text = reminders[position]
    }

    override fun getItemCount(): Int = reminders.size

    // Neue Methode, um Daten hinzuzufügen und den Adapter zu aktualisieren
    fun updateData(newReminder: String) {
        reminders.add(newReminder)
        notifyItemInserted(reminders.size - 1) // Nur das neue Element aktualisieren
    }
}

