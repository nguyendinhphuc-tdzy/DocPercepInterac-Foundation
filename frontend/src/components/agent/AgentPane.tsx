import React from 'react';
import { Bot, Send } from 'lucide-react';

const NOT_CONNECTED_MESSAGE = 'Chat is not connected to an AI model yet — this is a placeholder pane.';

export const AgentPane: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Pane Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
          <Bot size={16} />
          <span>AGENT</span>
        </div>
      </div>

      {/* Pane Content — honest empty state, no fake conversation */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center">
        <div className="text-center max-w-[240px]">
          <Bot size={24} className="mx-auto text-gray-300 mb-2" />
          <p className="text-sm text-gray-400">{NOT_CONNECTED_MESSAGE}</p>
        </div>
      </div>

      {/* Composer — disabled on purpose, not a fake working input */}
      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="relative" title={NOT_CONNECTED_MESSAGE}>
          <input
            type="text"
            placeholder="Ask Foundation… (not connected yet)"
            disabled
            className="w-full pl-3 pr-10 py-2 bg-gray-50 border border-gray-200 rounded-md text-sm text-gray-400 cursor-not-allowed"
          />
          <button disabled className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-300 cursor-not-allowed">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
