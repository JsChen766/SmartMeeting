import React from 'react';

export interface ActionItem {
  owner?: string;
  task: string;
}

export interface ActionItemListProps {
  items: ActionItem[];
}

export const ActionItemList: React.FC<ActionItemListProps> = ({ items }) => {
  if (!items || items.length === 0) {
    return (
      <div className="py-4 text-gray-500 italic text-sm">
        暫無行動項
      </div>
    );
  }

  return (
    <ul className="list-disc list-inside text-gray-800 space-y-2 pl-4">
      {items.map((item, index) => (
        <li key={index} className="flex flex-col sm:flex-row gap-2">
          {item.owner ? (
            <span className="font-semibold text-blue-600">[{item.owner}]</span>
          ) : (
            <span className="font-semibold text-gray-400">[未指定負責人]</span>
          )}
          <span className="text-gray-700">{item.task}</span>
        </li>
      ))}
    </ul>
  );
};
