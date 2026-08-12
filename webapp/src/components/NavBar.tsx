import { NavLink } from "react-router-dom";

const ITEMS = [
  { to: "/", icon: "◆", label: "Профиль" },
  { to: "/theory", icon: "▤", label: "Теория" },
  { to: "/mental-math", icon: "✳", label: "Счёт" },
  { to: "/portfolio", icon: "▲", label: "Портфель" },
];

export function NavBar() {
  return (
    <nav className="nav">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <span className="nav-item-icon">{item.icon}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
